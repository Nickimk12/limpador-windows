"""Limpador de arquivos temporários para Windows 10/11 - versão com interface gráfica."""

import ctypes
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

DIAS_PADRAO = 1
LOG_ARQUIVO = Path(__file__).resolve().parent / "limpador_log.txt"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # evita janelas de console piscando


# ---------------------------------------------------------------- utilidades

def is_admin():
    """Verifica se o programa está sendo executado como Administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevar_privilegios():
    """Reabre o programa como Administrador. Retorna False se o usuário recusar."""
    exe = sys.executable
    if getattr(sys, "frozen", False):  # caso vire .exe (PyInstaller)
        args = sys.argv[1:]
    else:
        pythonw = Path(exe).with_name("pythonw.exe")  # sem janela de console
        if pythonw.exists():
            exe = str(pythonw)
        args = [os.path.abspath(sys.argv[0])] + sys.argv[1:]
    params = subprocess.list2cmdline(args)
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return ret > 32


def formatar_tamanho(bytes_size):
    """Converte bytes para KB, MB ou GB."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    if bytes_size < 1024 ** 2:
        return f"{bytes_size / 1024:.2f} KB"
    if bytes_size < 1024 ** 3:
        return f"{bytes_size / (1024 ** 2):.2f} MB"
    return f"{bytes_size / (1024 ** 3):.2f} GB"


def log(mensagem):
    """Registra uma linha no arquivo de log (ao lado do programa)."""
    try:
        with open(LOG_ARQUIVO, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {mensagem}\n")
    except OSError:
        pass


# ------------------------------------------------------------ varredura/limpeza

def listar_arquivos(pasta, dias):
    """Gera (caminho, tamanho) dos arquivos com mais de `dias` dias (0 = todos)."""
    limite = time.time() - dias * 86400
    for raiz, _, arquivos in os.walk(pasta, onerror=lambda e: None):
        for nome in arquivos:
            caminho = os.path.join(raiz, nome)
            try:
                info = os.lstat(caminho)
            except OSError:
                continue
            if dias == 0 or info.st_mtime < limite:
                yield caminho, info.st_size


def escanear(pastas, dias):
    """Soma o que SERIA apagado, sem apagar nada (simulação)."""
    total = 0
    for pasta in pastas:
        if os.path.isdir(pasta):
            total += sum(tamanho for _, tamanho in listar_arquivos(pasta, dias))
    return total


def remover_pastas_vazias(pasta, dias):
    """Remove subpastas vazias (e antigas), de baixo para cima."""
    limite = time.time() - dias * 86400
    for raiz, _, _ in os.walk(pasta, topdown=False):
        if raiz == pasta:
            continue
        try:
            if dias == 0 or os.lstat(raiz).st_mtime < limite:
                os.rmdir(raiz)  # só funciona se estiver vazia
        except OSError:
            pass


def limpar(pastas, dias):
    """Apaga os arquivos antigos. Retorna (bytes liberados, arquivos removidos)."""
    liberado = 0
    removidos = 0
    for pasta in pastas:
        if not os.path.isdir(pasta):
            continue
        for caminho, tamanho in listar_arquivos(pasta, dias):
            try:
                os.unlink(caminho)
                liberado += tamanho
                removidos += 1
            except OSError:
                pass  # em uso ou sem permissão: ignora com segurança
        remover_pastas_vazias(pasta, dias)
    return liberado, removidos


# ------------------------------------------------------------ sistema/processos

def executar(cmd):
    """Roda um comando sem abrir janela e devolve o código de retorno."""
    try:
        return subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW).returncode
    except OSError:
        return -1


def processo_aberto(imagem):
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {imagem}"],
            capture_output=True, text=True, errors="ignore", creationflags=NO_WINDOW,
        )
        return imagem.lower() in r.stdout.lower()
    except OSError:
        return False


def servico_rodando(nome):
    try:
        r = subprocess.run(
            ["sc", "query", nome],
            capture_output=True, text=True, errors="ignore", creationflags=NO_WINDOW,
        )
        return "RUNNING" in r.stdout.upper()
    except OSError:
        return False


def esvaziar_lixeira():
    return executar(
        ["powershell.exe", "-NoProfile", "-Command",
         "Clear-RecycleBin -Force -ErrorAction Stop"]
    ) == 0


# ------------------------------------------------------------------ categorias

def pastas_navegador(base):
    """Cache de todos os perfis (Default, Profile 1, 2...) de um navegador Chromium."""
    user_data = Path(base) / "User Data"
    pastas = []
    if user_data.is_dir():
        for perfil in user_data.iterdir():
            if perfil.is_dir() and (perfil.name == "Default" or perfil.name.startswith("Profile ")):
                for sub in ("Cache", "Code Cache", "GPUCache"):
                    pastas.append(str(perfil / sub))
    return pastas


def montar_categorias():
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    local = os.environ.get("LOCALAPPDATA", "")

    return [
        {"nome": "Temporários do usuário",
         "pastas": [tempfile.gettempdir()], "padrao": True},
        {"nome": "Temporários do Windows",
         "pastas": [os.path.join(windir, "Temp")], "padrao": True},
        {"nome": "Cache do Windows Update",
         "pastas": [os.path.join(windir, "SoftwareDistribution", "Download")],
         "padrao": True, "servico": "wuauserv"},
        {"nome": "Relatórios de erro (CrashDumps)",
         "pastas": [os.path.join(local, "CrashDumps")], "padrao": True},
        {"nome": "Cache do Edge",
         "pastas": pastas_navegador(os.path.join(local, "Microsoft", "Edge")),
         "padrao": True, "processo": "msedge.exe"},
        {"nome": "Cache do Chrome",
         "pastas": pastas_navegador(os.path.join(local, "Google", "Chrome")),
         "padrao": True, "processo": "chrome.exe"},
        {"nome": "Cache do Brave",
         "pastas": pastas_navegador(os.path.join(local, "BraveSoftware", "Brave-Browser")),
         "padrao": True, "processo": "brave.exe"},
        # Opcionais: liberam pouco e/ou têm efeito colateral
        {"nome": "Prefetch (programas abrem mais lentos depois)",
         "pastas": [os.path.join(windir, "Prefetch")], "padrao": False},
        {"nome": "Logs do Windows (úteis para diagnóstico)",
         "pastas": [os.path.join(windir, "Logs")], "padrao": False},
        {"nome": "Lixeira (esvaziar)", "pastas": [], "padrao": False, "especial": "lixeira"},
    ]


# ------------------------------------------------------------------- interface

class App(tk.Tk):
    def __init__(self, admin):
        super().__init__()
        self.title("Limpador de Arquivos Temporários")
        self.geometry("780x700")
        self.minsize(700, 620)

        self.admin = admin
        self.categorias = montar_categorias()
        self.fila = queue.Queue()
        self.tamanhos = {}          # índice da categoria -> bytes (None = não calculado)
        self.dias_analisados = None
        self.ocupado = False
        self.limpando = False

        self.vars = []
        self.labels = []
        self._montar_ui()

        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(100, self._processar_fila)
        self.after(300, self.analisar)

    # ---- construção da tela

    def _montar_ui(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        raiz = ttk.Frame(self, padding=14)
        raiz.pack(fill="both", expand=True)

        ttk.Label(raiz, text="Limpador de Arquivos Temporários",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(raiz, text="Marque o que deseja limpar. Nada é apagado antes da sua confirmação.",
                  foreground="#555555").pack(anchor="w", pady=(0, 6))

        if not self.admin:
            ttk.Label(raiz, foreground="#b45309",
                      text="Sem permissão de Administrador: pastas do sistema podem não ser limpas."
                      ).pack(anchor="w", pady=(0, 6))

        topo = ttk.Frame(raiz)
        topo.pack(fill="x")
        ttk.Label(topo, text="Apagar só arquivos com mais de").pack(side="left")
        self.dias_var = tk.StringVar(value=str(DIAS_PADRAO))
        ttk.Spinbox(topo, from_=0, to=365, width=5, textvariable=self.dias_var).pack(side="left", padx=6)
        ttk.Label(topo, text="dia(s)   (0 = todos)").pack(side="left")

        caixa = ttk.LabelFrame(raiz, text="O que limpar", padding=10)
        caixa.pack(fill="x", pady=10)
        caixa.columnconfigure(0, weight=1)

        for i, cat in enumerate(self.categorias):
            var = tk.BooleanVar(value=cat["padrao"])
            ttk.Checkbutton(caixa, text=cat["nome"], variable=var,
                            command=self._atualizar_total).grid(row=i, column=0, sticky="w", pady=1)
            lbl = ttk.Label(caixa, text="—", width=16, anchor="e")
            lbl.grid(row=i, column=1, sticky="e")
            self.vars.append(var)
            self.labels.append(lbl)

        atalhos = ttk.Frame(raiz)
        atalhos.pack(fill="x")
        ttk.Button(atalhos, text="Recomendadas",
                   command=lambda: self._marcar("recomendadas")).pack(side="left")
        ttk.Button(atalhos, text="Todas",
                   command=lambda: self._marcar("todas")).pack(side="left", padx=6)
        ttk.Button(atalhos, text="Nenhuma",
                   command=lambda: self._marcar("nenhuma")).pack(side="left")

        self.total_var = tk.StringVar(value="Previsto para liberar: —")
        ttk.Label(raiz, textvariable=self.total_var,
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 4))

        acoes = ttk.Frame(raiz)
        acoes.pack(fill="x")
        self.btn_analisar = ttk.Button(acoes, text="Analisar de novo", command=self.analisar)
        self.btn_analisar.pack(side="left")
        self.btn_limpar = ttk.Button(acoes, text="Limpar selecionados", command=self.limpar_clicado)
        self.btn_limpar.pack(side="left", padx=6)
        ttk.Button(acoes, text="Abrir log", command=self._abrir_log).pack(side="right")

        self.barra = ttk.Progressbar(raiz, mode="indeterminate")
        self.barra.pack(fill="x", pady=(10, 6))

        self.txt = scrolledtext.ScrolledText(raiz, height=9, state="disabled", font=("Consolas", 9))
        self.txt.pack(fill="both", expand=True)

    # ---- helpers de interface

    def _log(self, texto):
        self.txt.configure(state="normal")
        self.txt.insert("end", texto + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _set_ocupado(self, flag):
        self.ocupado = flag
        estado = "disabled" if flag else "normal"
        self.btn_analisar.configure(state=estado)
        self.btn_limpar.configure(state=estado)
        if flag:
            self.barra.start(12)
        else:
            self.barra.stop()

    def _dias(self):
        try:
            return max(0, int(self.dias_var.get()))
        except ValueError:
            return DIAS_PADRAO

    def _marcar(self, modo):
        for var, cat in zip(self.vars, self.categorias):
            if modo == "todas":
                var.set(True)
            elif modo == "recomendadas":
                var.set(cat["padrao"])
            else:
                var.set(False)
        self._atualizar_total()

    def _previsto(self):
        return sum(self.tamanhos.get(i) or 0 for i, v in enumerate(self.vars) if v.get())

    def _atualizar_total(self):
        if self.dias_analisados is None:
            return
        self.total_var.set(f"Previsto para liberar: {formatar_tamanho(self._previsto())}")

    def _abrir_log(self):
        if not LOG_ARQUIVO.exists():
            messagebox.showinfo("Log", "Ainda não há log. Ele é criado na primeira limpeza.")
            return
        try:
            os.startfile(str(LOG_ARQUIVO))  # só existe no Windows
        except Exception:
            messagebox.showinfo("Log", f"O log está em:\n{LOG_ARQUIVO}")

    def _fechar(self):
        if self.limpando:
            messagebox.showinfo("Aguarde", "A limpeza está em andamento. Espere terminar para fechar.")
            return
        self.destroy()

    # ---- análise (simulação)

    def analisar(self):
        if self.ocupado:
            return
        dias = self._dias()
        self.dias_var.set(str(dias))
        self.tamanhos.clear()
        self.dias_analisados = None
        for lbl in self.labels:
            lbl.configure(text="analisando...")
        self.total_var.set("Previsto para liberar: calculando...")
        self._log(f"Analisando arquivos com mais de {dias} dia(s). Nada será apagado.")
        self._set_ocupado(True)
        threading.Thread(target=self._worker_analisar, args=(dias,), daemon=True).start()

    def _worker_analisar(self, dias):
        try:
            for i, cat in enumerate(self.categorias):
                if cat.get("especial") == "lixeira":
                    self.fila.put(("tamanho", i, None))
                else:
                    self.fila.put(("tamanho", i, escanear(cat["pastas"], dias)))
            self.fila.put(("analise_fim", dias))
        except Exception:
            self.fila.put(("erro", traceback.format_exc()))

    # ---- limpeza

    def limpar_clicado(self):
        if self.ocupado:
            return

        indices = [i for i, v in enumerate(self.vars) if v.get()]
        if not indices:
            messagebox.showinfo("Nada selecionado", "Marque pelo menos uma categoria.")
            return

        dias = self._dias()
        if self.dias_analisados != dias:
            messagebox.showinfo(
                "Analise primeiro",
                "O número de dias mudou. Clique em \"Analisar de novo\" para atualizar "
                "os tamanhos antes de limpar.",
            )
            return

        nomes = "\n".join("• " + self.categorias[i]["nome"] for i in indices)
        if not messagebox.askyesno(
            "Confirmar limpeza",
            f"Previsto para liberar: {formatar_tamanho(self._previsto())}\n\n"
            f"Categorias:\n{nomes}\n\n"
            "Os arquivos serão apagados permanentemente (não vão para a Lixeira).\n\n"
            "Continuar?",
            icon="warning",
        ):
            return

        abertos = [self.categorias[i]["nome"] for i in indices
                   if self.categorias[i].get("processo")
                   and processo_aberto(self.categorias[i]["processo"])]
        if abertos:
            if not messagebox.askyesno(
                "Navegadores abertos",
                "Estes navegadores estão abertos e parte do cache não será apagada:\n\n"
                + "\n".join("• " + n for n in abertos)
                + "\n\nContinuar mesmo assim?\n(Clique em Não para fechá-los antes.)",
                icon="warning",
            ):
                return

        self.limpando = True
        self._set_ocupado(True)
        self._log("-" * 50)
        threading.Thread(target=self._worker_limpar, args=(indices, dias), daemon=True).start()

    def _worker_limpar(self, indices, dias):
        total = 0
        try:
            log(f"Início da limpeza (arquivos com mais de {dias} dia(s))")
            for i in indices:
                cat = self.categorias[i]
                self.fila.put(("log", f"Limpando: {cat['nome']}..."))

                if cat.get("especial") == "lixeira":
                    ok = esvaziar_lixeira()
                    msg = ("Lixeira esvaziada." if ok
                           else "Não foi possível esvaziar a Lixeira (talvez já esteja vazia).")
                    self.fila.put(("log", "   " + msg))
                    log(f"Lixeira: {'ok' if ok else 'falhou'}")
                    continue

                servico = cat.get("servico")
                parou = False
                if servico and servico_rodando(servico):
                    parou = executar(["net", "stop", servico]) == 0

                try:
                    liberado, removidos = limpar(cat["pastas"], dias)
                finally:
                    if parou:
                        executar(["net", "start", servico])

                total += liberado
                self.fila.put(("log", f"   {removidos} arquivos removidos, "
                                      f"{formatar_tamanho(liberado)} liberados"))
                log(f"{cat['nome']}: {removidos} arquivos, {formatar_tamanho(liberado)} liberados")

            log(f"TOTAL liberado: {formatar_tamanho(total)}")
            self.fila.put(("limpeza_fim", total))
        except Exception:
            self.fila.put(("erro", traceback.format_exc()))

    # ---- comunicação thread -> interface

    def _processar_fila(self):
        try:
            while True:
                msg = self.fila.get_nowait()
                tipo = msg[0]

                if tipo == "log":
                    self._log(msg[1])

                elif tipo == "tamanho":
                    _, i, valor = msg
                    self.tamanhos[i] = valor
                    self.labels[i].configure(text="—" if valor is None else formatar_tamanho(valor))

                elif tipo == "analise_fim":
                    self.dias_analisados = msg[1]
                    self._set_ocupado(False)
                    self._atualizar_total()
                    self._log("Análise concluída.")

                elif tipo == "limpeza_fim":
                    total = msg[1]
                    self.limpando = False
                    self._set_ocupado(False)
                    self._log(f"TOTAL LIBERADO: {formatar_tamanho(total)}")
                    messagebox.showinfo("Concluído", f"Total liberado: {formatar_tamanho(total)}")
                    self.analisar()  # atualiza os tamanhos na tela

                elif tipo == "erro":
                    self.limpando = False
                    self._set_ocupado(False)
                    log(f"ERRO:\n{msg[1]}")
                    self._log("Ocorreu um erro inesperado:\n" + msg[1])
                    messagebox.showerror("Erro", "Ocorreu um erro inesperado. Veja os detalhes no log.")
        except queue.Empty:
            pass
        self.after(100, self._processar_fila)


# ------------------------------------------------------------------------ main

def main():
    if os.name != "nt":
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Sistema não suportado", "Este programa funciona apenas no Windows.")
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # textos nítidos em telas de alta resolução
    except Exception:
        pass

    admin = is_admin()
    if not admin:
        root = tk.Tk()
        root.withdraw()
        quer = messagebox.askyesno(
            "Permissão de Administrador",
            "Para limpar as pastas do sistema, o programa precisa ser aberto como Administrador.\n\n"
            "Reabrir agora como Administrador?\n\n"
            "(Se escolher Não, só as pastas do seu usuário serão limpas com segurança.)",
        )
        root.destroy()
        if quer:
            if elevar_privilegios():
                return
            messagebox.showwarning("Elevação cancelada", "Continuando sem permissão de Administrador.")

    App(admin).mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        erro = traceback.format_exc()
        log(f"ERRO:\n{erro}")
        try:
            messagebox.showerror("Erro inesperado", erro)
        except Exception:
            print(erro)