import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import platform
import socket
import ipaddress
import threading
import json
import os
import sys
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


NOMBRE_APP = "ControlRed"


def ruta_ejecutable():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def ruta_meipass():
    return getattr(sys, "_MEIPASS", None)


def ruta_datos_app():
    base = os.getenv("LOCALAPPDATA")
    if not base:
        base = os.path.expanduser("~\\AppData\\Local")

    carpeta_app = os.path.join(base, NOMBRE_APP)
    os.makedirs(carpeta_app, exist_ok=True)
    return carpeta_app


def ruta_recurso(nombre_archivo):
    ruta_local = os.path.join(ruta_ejecutable(), nombre_archivo)
    if os.path.exists(ruta_local):
        return ruta_local

    carpeta_temp = ruta_meipass()
    if carpeta_temp:
        ruta_temp = os.path.join(carpeta_temp, nombre_archivo)
        if os.path.exists(ruta_temp):
            return ruta_temp

    return ruta_local


def inicializar_archivo_json(nombre_archivo):
    ruta_destino = os.path.join(ruta_datos_app(), nombre_archivo)

    if os.path.exists(ruta_destino):
        return ruta_destino

    try:
        with open(ruta_destino, "w", encoding="utf-8") as archivo:
            json.dump({}, archivo, indent=4, ensure_ascii=False)
    except Exception:
        pass

    return ruta_destino


def ejecutar_oculto(comando):
    if platform.system().lower() == "windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.run(
            comando,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    return subprocess.run(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def ejecutar_oculto_salida(comando):
    if platform.system().lower() == "windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.check_output(
            comando,
            text=True,
            encoding="utf-8",
            errors="ignore",
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    return subprocess.check_output(
        comando,
        text=True,
        encoding="utf-8",
        errors="ignore",
        stderr=subprocess.DEVNULL
    )


def centrar_ventana(ventana, ancho, alto):
    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()

    posicion_x = max(0, int((pantalla_ancho / 2) - (ancho / 2)))
    posicion_y = max(0, int((pantalla_alto / 2) - (alto / 2)))

    ventana.geometry(f"{ancho}x{alto}+{posicion_x}+{posicion_y}")


escaneando = False
actualizacion_automatica = True
intervalo_segundos = 5
dispositivos_visibles = {}

ARCHIVO_ALIAS = inicializar_archivo_json("alias_dispositivos.json")
ARCHIVO_HISTORIAL = inicializar_archivo_json("historial_dispositivos.json")

FABRICANTES_OUI = {
    "00:1a:11": "Google o Nest",
    "00:1b:63": "Apple",
    "00:1c:b3": "Apple",
    "00:1d:d8": "Apple",
    "00:1e:c2": "Apple",
    "28:cf:e9": "Apple",
    "3c:06:30": "Apple",
    "40:b0:34": "Apple",
    "60:f8:1d": "Apple",
    "a4:83:e7": "Apple",
    "b8:27:eb": "Raspberry Pi",
    "dc:a6:32": "Raspberry Pi",
    "e4:5f:01": "Raspberry Pi",
    "00:e0:4c": "Realtek",
    "00:0c:29": "VMware",
    "00:50:56": "VMware",
    "08:00:27": "VirtualBox",
    "f4:f5:d8": "Samsung",
    "a8:9c:ed": "Samsung",
    "fc:a1:3e": "Samsung",
    "00:16:6c": "Samsung",
    "2c:54:cf": "LG",
    "10:08:b1": "LG",
    "64:bc:0c": "LG",
    "00:1f:a3": "Sony",
    "70:9e:29": "Sony",
    "00:90:4c": "EpSon o impresora",
    "18:fe:34": "Espressif o IoT",
    "24:6f:28": "Espressif o IoT",
    "84:f3:eb": "Xiaomi",
    "64:09:80": "Xiaomi",
    "44:65:0d": "Xiaomi",
    "00:e0:fc": "Huawei",
    "d4:6a:6a": "Huawei",
    "c8:d7:19": "Huawei",
    "00:25:9c": "Cisco",
    "00:40:96": "Cisco",
    "3c:37:86": "Cisco",
    "9c:b6:d0": "TP Link",
    "50:c7:bf": "TP Link",
    "f4:f2:6d": "TP Link",
}

COLORES = {
    "fondo": "#060b16",
    "panel": "#0f172a",
    "panel_sec": "#111c34",
    "borde": "#22304d",
    "texto": "#e5eefc",
    "texto_sec": "#91a4c3",
    "azul": "#3b82f6",
    "azul_hover": "#2563eb",
    "verde": "#22c55e",
    "amarillo": "#f59e0b",
    "rojo": "#ef4444",
    "gris_btn": "#1f2937",
    "gris_hover": "#374151",
    "tabla": "#0b1220",
    "tabla_alt": "#0d1629",
}


def cargar_alias():
    if not os.path.exists(ARCHIVO_ALIAS):
        try:
            with open(ARCHIVO_ALIAS, "w", encoding="utf-8") as archivo:
                json.dump({}, archivo, indent=4, ensure_ascii=False)
        except Exception:
            return {}
        return {}

    try:
        with open(ARCHIVO_ALIAS, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return {}


def guardar_alias(alias_dict):
    try:
        with open(ARCHIVO_ALIAS, "w", encoding="utf-8") as archivo:
            json.dump(alias_dict, archivo, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron guardar los alias.\n{e}")


alias_guardados = cargar_alias()


def cargar_historial():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as archivo:
                json.dump({}, archivo, indent=4, ensure_ascii=False)
        except Exception:
            return {}
        return {}

    try:
        with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return {}


def guardar_historial(historial_dict):
    try:
        with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as archivo:
            json.dump(historial_dict, archivo, indent=4, ensure_ascii=False)
    except Exception:
        pass


historial_conexiones = cargar_historial()


def obtener_clave_dispositivo(ip, mac):
    if mac and mac != "Desconocida":
        return f"mac::{mac.lower()}"
    return f"ip::{ip}"


def registrar_primera_deteccion(ip, mac):
    clave = obtener_clave_dispositivo(ip, mac)
    fecha_guardada = historial_conexiones.get(clave)

    if fecha_guardada:
        return fecha_guardada

    ahora = datetime.now().isoformat(timespec="seconds")
    historial_conexiones[clave] = ahora
    guardar_historial(historial_conexiones)
    return ahora


def formatear_fecha_conexion(fecha_iso):
    try:
        fecha = datetime.fromisoformat(fecha_iso)
        return fecha.strftime("%d/%m/%Y %I:%M:%S %p")
    except Exception:
        return "No disponible"


def obtener_fecha_conexion(ip, mac):
    fecha_iso = registrar_primera_deteccion(ip, mac)
    return formatear_fecha_conexion(fecha_iso), fecha_iso


def obtener_red_local():
    try:
        hostname = socket.gethostname()
        ip_local = socket.gethostbyname(hostname)

        if ip_local.startswith("127."):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()

        red = ipaddress.ip_network(f"{ip_local}/24", strict=False)
        return red
    except Exception:
        return None


def obtener_ip_local():
    try:
        hostname = socket.gethostname()
        ip_local = socket.gethostbyname(hostname)

        if ip_local.startswith("127."):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()

        return ip_local
    except Exception:
        return "No disponible"


def obtener_gateway():
    try:
        sistema = platform.system().lower()

        if sistema == "windows":
            resultado = ejecutar_oculto_salida(["ipconfig"])

            for linea in resultado.splitlines():
                if "Puerta de enlace predeterminada" in linea or "Default Gateway" in linea:
                    partes = linea.split(":", 1)
                    if len(partes) > 1:
                        gateway = partes[1].strip()
                        if gateway and gateway != ".":
                            return gateway
        else:
            resultado = ejecutar_oculto_salida(["ip", "route"])

            for linea in resultado.splitlines():
                if linea.startswith("default via "):
                    partes = linea.split()
                    if len(partes) >= 3:
                        return partes[2]

        return None
    except Exception:
        return None


def obtener_nombre_red():
    try:
        if platform.system().lower() == "windows":
            resultado = ejecutar_oculto_salida(["netsh", "wlan", "show", "interfaces"])

            for linea in resultado.splitlines():
                if "SSID" in linea and "BSSID" not in linea:
                    partes = linea.split(":", 1)
                    if len(partes) > 1:
                        nombre = partes[1].strip()
                        if nombre:
                            return nombre

        return "Red no identificada"
    except Exception:
        return "Red no identificada"


def hacer_ping(ip):
    sistema = platform.system().lower()

    if sistema == "windows":
        comando = ["ping", "-n", "1", "-w", "300", str(ip)]
    else:
        comando = ["ping", "-c", "1", "-W", "1", str(ip)]

    try:
        resultado = ejecutar_oculto(comando)
        return resultado.returncode == 0
    except Exception:
        return False


def verificar_estado_red():
    try:
        sistema = platform.system().lower()

        if sistema == "windows":
            comando = ["ping", "-n", "1", "-w", "1000", "8.8.8.8"]
        else:
            comando = ["ping", "-c", "1", "-W", "1", "8.8.8.8"]

        resultado = ejecutar_oculto(comando)
        return resultado.returncode == 0
    except Exception:
        return False


def obtener_nombre_equipo(ip):
    try:
        nombre, _, _ = socket.gethostbyaddr(str(ip))
        return nombre
    except Exception:
        return "Sin nombre visible"


def obtener_mac(ip):
    try:
        if platform.system().lower() == "windows":
            resultado = ejecutar_oculto_salida(["arp", "-a", ip])
        else:
            resultado = ejecutar_oculto_salida(["arp", "-n", ip])

        for linea in resultado.splitlines():
            if ip in linea:
                partes = linea.split()
                for parte in partes:
                    texto = parte.strip().lower().replace("-", ":")
                    if texto.count(":") == 5:
                        return texto

        return "Desconocida"
    except Exception:
        return "Desconocida"


def obtener_fabricante(mac):
    if not mac or mac == "Desconocida":
        return "No identificado"

    oui = mac.lower().replace("-", ":")[0:8]
    return FABRICANTES_OUI.get(oui, "Fabricante no identificado")


def obtener_nombre_mostrado(ip, mac, nombre_host):
    if mac in alias_guardados:
        return alias_guardados[mac]
    if nombre_host and nombre_host != "Sin nombre visible":
        return nombre_host
    return ip


def actualizar_contador():
    cantidad_valor.config(text=str(len(dispositivos_visibles)))
    total_tabla_valor.config(text=f"{len(dispositivos_visibles)} dispositivos visibles")


def marcar_como_activo(ip):
    if ip in dispositivos_visibles:
        datos = dispositivos_visibles[ip]
        tabla.item(
            datos["item"],
            values=(ip, datos["nombre"], datos["mac"], datos["fabricante"], datos["desde"], "Activo"),
            tags=("activo",)
        )
        dispositivos_visibles[ip]["estado"] = "Activo"


def refrescar_estilo_filas():
    for idx, (ip, datos) in enumerate(sorted(dispositivos_visibles.items(), key=lambda x: tuple(map(int, x[0].split("."))))):
        estado = datos.get("estado", "Activo")
        base_tag = "par" if idx % 2 == 0 else "impar"
        if estado == "Nuevo":
            tabla.item(datos["item"], tags=(base_tag, "nuevo"))
        else:
            tabla.item(datos["item"], tags=(base_tag, "activo"))


def agregar_o_actualizar_dispositivo(ip, nombre, mac, fabricante):
    fecha_desde, fecha_iso = obtener_fecha_conexion(ip, mac)

    if ip in dispositivos_visibles:
        item_id = dispositivos_visibles[ip]["item"]
        fecha_mostrada = dispositivos_visibles[ip].get("desde", fecha_desde)
        fecha_guardada = dispositivos_visibles[ip].get("desde_iso", fecha_iso)

        tabla.item(item_id, values=(ip, nombre, mac, fabricante, fecha_mostrada, "Activo"))
        dispositivos_visibles[ip]["nombre"] = nombre
        dispositivos_visibles[ip]["mac"] = mac
        dispositivos_visibles[ip]["fabricante"] = fabricante
        dispositivos_visibles[ip]["desde"] = fecha_mostrada
        dispositivos_visibles[ip]["desde_iso"] = fecha_guardada
        dispositivos_visibles[ip]["estado"] = "Activo"
    else:
        item_id = tabla.insert("", tk.END, values=(ip, nombre, mac, fabricante, fecha_desde, "Nuevo"), tags=("nuevo",))
        dispositivos_visibles[ip] = {
            "item": item_id,
            "nombre": nombre,
            "mac": mac,
            "fabricante": fabricante,
            "desde": fecha_desde,
            "desde_iso": fecha_iso,
            "estado": "Nuevo"
        }
        ventana.after(3000, lambda: marcar_como_activo(ip))

    actualizar_contador()
    refrescar_estilo_filas()


def eliminar_dispositivos_desconectados(ips_detectadas):
    ips_actuales = set(dispositivos_visibles.keys())
    ips_a_eliminar = ips_actuales - ips_detectadas

    for ip in ips_a_eliminar:
        item_id = dispositivos_visibles[ip]["item"]
        tabla.delete(item_id)
        del dispositivos_visibles[ip]

    actualizar_contador()
    refrescar_estilo_filas()


def ordenar_tabla():
    filas = []
    for ip, datos in dispositivos_visibles.items():
        filas.append((ip, datos["item"]))

    filas.sort(key=lambda x: tuple(map(int, x[0].split("."))))

    for index, (_, item_id) in enumerate(filas):
        tabla.move(item_id, "", index)

    refrescar_estilo_filas()


def actualizar_estado_visual_red():
    red_ok = verificar_estado_red()

    if red_ok:
        red_estado_valor.config(text="Conectada y estable", fg=COLORES["verde"])
        red_estado_punto.config(fg=COLORES["verde"])
        estado_texto.config(text="Red funcionando sin problemas")
        insignia_estado.config(text="Operativa", bg="#12351f", fg="#86efac")
    else:
        red_estado_valor.config(text="Posible problema de conexión", fg=COLORES["rojo"])
        red_estado_punto.config(fg=COLORES["rojo"])
        estado_texto.config(text="Se detectó un posible problema de red")
        insignia_estado.config(text="Atención", bg="#3b1616", fg="#fca5a5")


def finalizar_escaneo(total):
    global escaneando
    escaneando = False
    actualizar_estado_visual_red()
    estado_punto.config(fg=COLORES["verde"])
    escaneo_valor.config(text="En espera")


def escanear_red():
    global escaneando

    if escaneando:
        return

    escaneando = True
    estado_texto.config(text="Analizando dispositivos en la red...")
    estado_punto.config(fg=COLORES["amarillo"])
    escaneo_valor.config(text="Escaneando")

    nombre_red_valor.config(text=obtener_nombre_red())
    ip_local_valor.config(text=obtener_ip_local())

    hilo = threading.Thread(target=escanear_red_en_segundo_plano, daemon=True)
    hilo.start()


def escanear_red_en_segundo_plano():
    red = obtener_red_local()
    gateway = obtener_gateway()

    if red is None:
        ventana.after(0, lambda: messagebox.showerror("Error", "No se pudo detectar la red local."))
        ventana.after(0, lambda: finalizar_escaneo(0))
        return

    dispositivos_detectados = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {executor.submit(hacer_ping, ip): ip for ip in red.hosts()}

        for futuro in as_completed(futuros):
            ip = futuros[futuro]
            try:
                activo = futuro.result()
                if activo:
                    ip_str = str(ip)

                    if gateway and ip_str == gateway:
                        continue

                    nombre_host = obtener_nombre_equipo(ip_str)
                    mac = obtener_mac(ip_str)
                    fabricante = obtener_fabricante(mac)
                    nombre_mostrado = obtener_nombre_mostrado(ip_str, mac, nombre_host)

                    dispositivos_detectados.append(ip_str)
                    ventana.after(
                        0,
                        agregar_o_actualizar_dispositivo,
                        ip_str,
                        nombre_mostrado,
                        mac,
                        fabricante
                    )
            except Exception:
                pass

    ips_detectadas = set(dispositivos_detectados)

    ventana.after(0, eliminar_dispositivos_desconectados, ips_detectadas)
    ventana.after(0, ordenar_tabla)
    ventana.after(0, lambda: finalizar_escaneo(len(ips_detectadas)))


def ciclo_automatico():
    if actualizacion_automatica and not escaneando:
        escanear_red()

    ventana.after(intervalo_segundos * 1000, ciclo_automatico)


def asignar_alias():
    seleccionado = tabla.selection()
    if not seleccionado:
        messagebox.showinfo("Aviso", "Selecciona un dispositivo de la tabla.")
        return

    item_id = seleccionado[0]
    valores = tabla.item(item_id, "values")

    if len(valores) < 6:
        return

    ip = valores[0]
    nombre_actual = valores[1]
    mac = valores[2]

    if mac == "Desconocida":
        messagebox.showwarning("Aviso", "Este dispositivo no tiene MAC identificada.")
        return

    nuevo_alias = simpledialog.askstring(
        "Asignar alias",
        f"Alias para el dispositivo\n\nIP: {ip}\nMAC: {mac}",
        initialvalue=nombre_actual,
        parent=ventana
    )

    if nuevo_alias is None:
        return

    nuevo_alias = nuevo_alias.strip()
    if not nuevo_alias:
        messagebox.showwarning("Aviso", "El alias no puede estar vacío.")
        return

    alias_guardados[mac] = nuevo_alias
    guardar_alias(alias_guardados)

    if ip in dispositivos_visibles:
        dispositivos_visibles[ip]["nombre"] = nuevo_alias
        datos = dispositivos_visibles[ip]
        tabla.item(
            datos["item"],
            values=(ip, nuevo_alias, datos["mac"], datos["fabricante"], datos["desde"], datos["estado"])
        )


def eliminar_alias():
    seleccionado = tabla.selection()
    if not seleccionado:
        messagebox.showinfo("Aviso", "Selecciona un dispositivo de la tabla.")
        return

    item_id = seleccionado[0]
    valores = tabla.item(item_id, "values")

    if len(valores) < 6:
        return

    mac = valores[2]

    if mac in alias_guardados:
        del alias_guardados[mac]
        guardar_alias(alias_guardados)
        escanear_red()
    else:
        messagebox.showinfo("Aviso", "Ese dispositivo no tiene alias guardado.")


def crear_tarjeta_info(contenedor, titulo, valor_inicial, subtitulo_inicial=""):
    tarjeta = tk.Frame(contenedor, bg=COLORES["panel"], highlightbackground=COLORES["borde"], highlightthickness=1)
    tarjeta.grid_propagate(False)

    titulo_lbl = tk.Label(
        tarjeta,
        text=titulo,
        font=("Segoe UI", 10),
        bg=COLORES["panel"],
        fg=COLORES["texto_sec"]
    )
    titulo_lbl.pack(anchor="w", padx=18, pady=(16, 6))

    valor_lbl = tk.Label(
        tarjeta,
        text=valor_inicial,
        font=("Segoe UI Semibold", 18),
        bg=COLORES["panel"],
        fg=COLORES["texto"],
        wraplength=260,
        justify="left"
    )
    valor_lbl.pack(anchor="w", padx=18)

    subtitulo_lbl = tk.Label(
        tarjeta,
        text=subtitulo_inicial,
        font=("Segoe UI", 10),
        bg=COLORES["panel"],
        fg="#c4d2ea",
        wraplength=260,
        justify="left"
    )
    subtitulo_lbl.pack(anchor="w", padx=18, pady=(8, 16))

    return tarjeta, valor_lbl, subtitulo_lbl


ventana = tk.Tk()

if platform.system().lower() == "windows":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("control.red.monitor.app")
    except Exception:
        pass

ruta_icono = ruta_recurso("logo.ico")
if os.path.exists(ruta_icono):
    try:
        ventana.iconbitmap(default=ruta_icono)
    except Exception:
        try:
            ventana.wm_iconbitmap(ruta_icono)
        except Exception:
            pass

ventana.title("Centro de monitoreo de red")
centrar_ventana(ventana, 1380, 820)
ventana.minsize(1080, 640)
ventana.configure(bg=COLORES["fondo"])

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Treeview",
    background=COLORES["tabla"],
    foreground=COLORES["texto"],
    fieldbackground=COLORES["tabla"],
    rowheight=38,
    font=("Segoe UI", 10),
    borderwidth=0,
    relief="flat"
)

style.configure(
    "Treeview.Heading",
    background=COLORES["panel_sec"],
    foreground=COLORES["texto"],
    font=("Segoe UI Semibold", 10),
    relief="flat",
    borderwidth=0,
    padding=(8, 12)
)

style.map(
    "Treeview",
    background=[("selected", COLORES["azul"])],
    foreground=[("selected", "white")]
)

style.map(
    "Treeview.Heading",
    background=[("active", "#182743")]
)

contenedor = tk.Frame(ventana, bg=COLORES["fondo"])
contenedor.pack(fill="both", expand=True, padx=18, pady=18)
contenedor.grid_columnconfigure(0, weight=1)
contenedor.grid_rowconfigure(2, weight=1)

encabezado = tk.Frame(contenedor, bg=COLORES["panel"], highlightbackground=COLORES["borde"], highlightthickness=1)
encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 16))
encabezado.grid_columnconfigure(0, weight=1)
encabezado.grid_columnconfigure(1, weight=0)

zona_texto = tk.Frame(encabezado, bg=COLORES["panel"])
zona_texto.grid(row=0, column=0, sticky="w", padx=24, pady=22)

etiqueta_superior = tk.Label(
    zona_texto,
    text="Panel inteligente de supervisión",
    font=("Segoe UI Semibold", 10),
    bg=COLORES["panel"],
    fg="#7dd3fc"
)
etiqueta_superior.pack(anchor="w")

titulo = tk.Label(
    zona_texto,
    text="Centro de monitoreo de red",
    font=("Segoe UI Semibold", 24),
    bg=COLORES["panel"],
    fg=COLORES["texto"]
)
titulo.pack(anchor="w", pady=(6, 6))

subtitulo = tk.Label(
    zona_texto,
    text="Visualiza dispositivos conectados, identifica fabricantes y organiza alias desde una vista más moderna.",
    font=("Segoe UI", 10),
    bg=COLORES["panel"],
    fg=COLORES["texto_sec"],
    wraplength=800,
    justify="left"
)
subtitulo.pack(anchor="w")

zona_estado = tk.Frame(encabezado, bg=COLORES["panel"])
zona_estado.grid(row=0, column=1, sticky="e", padx=24, pady=22)

insignia_estado = tk.Label(
    zona_estado,
    text="Inicializando",
    font=("Segoe UI Semibold", 10),
    bg="#172554",
    fg="#bfdbfe",
    padx=16,
    pady=8
)
insignia_estado.pack(anchor="e")

panel_tarjetas = tk.Frame(contenedor, bg=COLORES["fondo"])
panel_tarjetas.grid(row=1, column=0, sticky="ew", pady=(0, 16))
for i in range(4):
    panel_tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjetas")

card_red, nombre_red_valor, ip_local_valor = crear_tarjeta_info(
    panel_tarjetas,
    "Red actual",
    "Cargando...",
    "IP local"
)
card_red.grid(row=0, column=0, sticky="nsew", padx=(0, 8), ipadx=4, ipady=4)

card_estado, red_estado_valor, estado_aux = crear_tarjeta_info(
    panel_tarjetas,
    "Estado de la red",
    "Verificando...",
    "Conectividad general"
)
card_estado.grid(row=0, column=1, sticky="nsew", padx=8, ipadx=4, ipady=4)

fila_estado_red = tk.Frame(card_estado, bg=COLORES["panel"])
fila_estado_red.place(relx=1.0, x=-18, y=18, anchor="ne")
red_estado_punto = tk.Label(
    fila_estado_red,
    text="●",
    font=("Segoe UI", 12),
    bg=COLORES["panel"],
    fg=COLORES["verde"]
)
red_estado_punto.pack()

card_dispositivos, cantidad_valor, total_tabla_valor = crear_tarjeta_info(
    panel_tarjetas,
    "Dispositivos activos",
    "0",
    "0 dispositivos visibles"
)
card_dispositivos.grid(row=0, column=2, sticky="nsew", padx=8, ipadx=4, ipady=4)

card_escaneo, escaneo_valor, escaneo_sub = crear_tarjeta_info(
    panel_tarjetas,
    "Motor de escaneo",
    "En espera",
    f"Actualización automática cada {intervalo_segundos} segundos"
)
card_escaneo.grid(row=0, column=3, sticky="nsew", padx=(8, 0), ipadx=4, ipady=4)

panel_monitor = tk.Frame(contenedor, bg=COLORES["panel"], highlightbackground=COLORES["borde"], highlightthickness=1)
panel_monitor.grid(row=2, column=0, sticky="nsew")
panel_monitor.grid_columnconfigure(0, weight=1)
panel_monitor.grid_rowconfigure(2, weight=1)

barra_superior = tk.Frame(panel_monitor, bg=COLORES["panel"])
barra_superior.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
barra_superior.grid_columnconfigure(0, weight=1)

zona_titulo_tabla = tk.Frame(barra_superior, bg=COLORES["panel"])
zona_titulo_tabla.grid(row=0, column=0, sticky="w")

titulo_tabla = tk.Label(
    zona_titulo_tabla,
    text="Dispositivos detectados",
    font=("Segoe UI Semibold", 14),
    bg=COLORES["panel"],
    fg=COLORES["texto"]
)
titulo_tabla.pack(anchor="w")

subtitulo_tabla = tk.Label(
    zona_titulo_tabla,
    text="Vista central del monitoreo en tiempo real",
    font=("Segoe UI", 9),
    bg=COLORES["panel"],
    fg=COLORES["texto_sec"]
)
subtitulo_tabla.pack(anchor="w", pady=(3, 0))

acciones = tk.Frame(barra_superior, bg=COLORES["panel"])
acciones.grid(row=0, column=1, sticky="e")

btn_estilo = {
    "font": ("Segoe UI Semibold", 10),
    "fg": "white",
    "relief": "flat",
    "padx": 16,
    "pady": 9,
    "cursor": "hand2",
    "bd": 0,
}

btn_alias = tk.Button(
    acciones,
    text="Asignar alias",
    command=asignar_alias,
    bg=COLORES["azul"],
    activebackground=COLORES["azul_hover"],
    activeforeground="white",
    **btn_estilo
)
btn_alias.pack(side="left", padx=(0, 10))

btn_quitar_alias = tk.Button(
    acciones,
    text="Quitar alias",
    command=eliminar_alias,
    bg=COLORES["gris_btn"],
    activebackground=COLORES["gris_hover"],
    activeforeground="white",
    **btn_estilo
)
btn_quitar_alias.pack(side="left")

fila_estado_monitor = tk.Frame(panel_monitor, bg=COLORES["panel_sec"])
fila_estado_monitor.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

estado_punto = tk.Label(
    fila_estado_monitor,
    text="●",
    font=("Segoe UI", 14),
    bg=COLORES["panel_sec"],
    fg=COLORES["verde"]
)
estado_punto.pack(side="left", padx=(14, 8), pady=10)

estado_texto = tk.Label(
    fila_estado_monitor,
    text="Iniciando monitor...",
    font=("Segoe UI", 10),
    bg=COLORES["panel_sec"],
    fg="#d6e2f5"
)
estado_texto.pack(side="left", pady=10)

marco_tabla = tk.Frame(panel_monitor, bg=COLORES["panel"])
marco_tabla.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
marco_tabla.grid_columnconfigure(0, weight=1)
marco_tabla.grid_rowconfigure(0, weight=1)

scroll_y = ttk.Scrollbar(marco_tabla, orient="vertical")
scroll_y.grid(row=0, column=1, sticky="ns")

scroll_x = ttk.Scrollbar(marco_tabla, orient="horizontal")
scroll_x.grid(row=1, column=0, sticky="ew")

tabla = ttk.Treeview(
    marco_tabla,
    columns=("ip", "nombre", "mac", "fabricante", "desde", "estado"),
    show="headings",
    yscrollcommand=scroll_y.set,
    xscrollcommand=scroll_x.set
)

tabla.heading("ip", text="Dirección IP")
tabla.heading("nombre", text="Nombre o alias")
tabla.heading("mac", text="MAC")
tabla.heading("fabricante", text="Fabricante")
tabla.heading("desde", text="Conectado desde")
tabla.heading("estado", text="Estado")

tabla.column("ip", width=150, minwidth=130, anchor="center")
tabla.column("nombre", width=260, minwidth=190, anchor="center")
tabla.column("mac", width=180, minwidth=170, anchor="center")
tabla.column("fabricante", width=240, minwidth=210, anchor="center")
tabla.column("desde", width=220, minwidth=210, anchor="center")
tabla.column("estado", width=120, minwidth=110, anchor="center")

tabla.grid(row=0, column=0, sticky="nsew")
scroll_y.config(command=tabla.yview)
scroll_x.config(command=tabla.xview)

tabla.tag_configure("par", background=COLORES["tabla"], foreground=COLORES["texto"])
tabla.tag_configure("impar", background=COLORES["tabla_alt"], foreground=COLORES["texto"])
tabla.tag_configure("nuevo", background="#10203c", foreground="#bfdbfe")
tabla.tag_configure("activo", foreground=COLORES["texto"])

ventana.after(500, escanear_red)
ventana.after(intervalo_segundos * 1000, ciclo_automatico)

ventana.mainloop()