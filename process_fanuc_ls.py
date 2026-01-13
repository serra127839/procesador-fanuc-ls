#!/usr/bin/env python3
"""
Script para procesar archivos .ls de Fanuc añadiendo IDs de puntos de soldadura.

Uso:
    # Modo interfaz gráfica (recomendado)
    python process_fanuc_ls.py
    
    # Modo línea de comandos
    python process_fanuc_ls.py <directorio_entrada> <directorio_salida>

Ejemplo:
    python process_fanuc_ls.py
    python process_fanuc_ls.py ./programas_originales ./programas_modificados

Características:
- Procesa recursivamente todos los subdirectorios
- Reproduce la estructura de directorios en la salida
- Limpia el directorio de salida antes de empezar
"""

import re
import os
import sys
import shutil
from pathlib import Path

# Importar tkinter solo si está disponible
try:
    from tkinter import Tk, filedialog, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


def select_directories_gui():
    """
    Muestra diálogos gráficos para seleccionar directorios de entrada y salida.
    
    Returns:
        tuple: (input_dir, output_dir) o (None, None) si se cancela
    """
    if not TKINTER_AVAILABLE:
        print("\nError: La interfaz gráfica no está disponible.")
        print("El módulo tkinter no está instalado en tu sistema.")
        print("\nPor favor, usa el modo línea de comandos:")
        print(f"    python {sys.argv[0]} <directorio_entrada> <directorio_salida>")
        return None, None
    
    # Crear ventana raíz oculta
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # Seleccionar directorio de entrada
    messagebox.showinfo(
        "Seleccionar Directorio de Entrada",
        "Por favor, selecciona el directorio donde están los archivos .ls originales.\n\n"
        "El script buscará archivos .ls en este directorio y todos sus subdirectorios."
    )
    
    input_dir = filedialog.askdirectory(
        title="Seleccionar Directorio de ENTRADA (archivos originales .ls)",
        mustexist=True
    )
    
    if not input_dir:
        messagebox.showwarning("Cancelado", "No se seleccionó directorio de entrada.\nOperación cancelada.")
        root.destroy()
        return None, None
    
    # Seleccionar directorio de salida
    messagebox.showinfo(
        "Seleccionar Directorio de Salida",
        "Por favor, selecciona el directorio donde se guardarán los archivos modificados.\n\n"
        "⚠️ ADVERTENCIA:\n"
        "Si el directorio ya existe, TODO su contenido será eliminado.\n"
        "La estructura de subdirectorios se reproducirá automáticamente."
    )
    
    output_dir = filedialog.askdirectory(
        title="Seleccionar Directorio de SALIDA (archivos modificados)"
    )
    
    if not output_dir:
        messagebox.showwarning("Cancelado", "No se seleccionó directorio de salida.\nOperación cancelada.")
        root.destroy()
        return None, None
    
    # Verificar que no sean el mismo directorio
    if Path(input_dir).resolve() == Path(output_dir).resolve():
        messagebox.showerror(
            "Error",
            "ERROR: Los directorios de entrada y salida no pueden ser el mismo.\n\n"
            "Esto borraría todos tus archivos originales."
        )
        root.destroy()
        return None, None
    
    # Mostrar resumen y confirmar
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Contar archivos .ls
    ls_files = list(input_path.rglob('*.ls'))
    
    if not ls_files:
        messagebox.showwarning(
            "Sin archivos",
            f"No se encontraron archivos .ls en:\n{input_dir}\n\n"
            "Verifica que el directorio sea correcto."
        )
        root.destroy()
        return None, None
    
    confirm_msg = (
        f"RESUMEN DE LA OPERACIÓN:\n\n"
        f"📂 Entrada:  {input_dir}\n"
        f"📁 Salida:   {output_dir}\n"
        f"📄 Archivos encontrados: {len(ls_files)}\n\n"
    )
    
    if output_path.exists() and any(output_path.iterdir()):
        confirm_msg += (
            "⚠️ ADVERTENCIA:\n"
            "El directorio de salida existe y contiene archivos.\n"
            "TODO su contenido será ELIMINADO antes de procesar.\n\n"
        )
    
    confirm_msg += "¿Deseas continuar?"
    
    confirm = messagebox.askyesno(
        "Confirmar Procesamiento",
        confirm_msg,
        icon='warning'
    )
    
    root.destroy()
    
    if not confirm:
        print("\nOperación cancelada por el usuario.")
        return None, None
    
    return input_dir, output_dir


def clean_output_directory(output_dir, silent=False):
    """
    Limpia completamente el directorio de salida (elimina todo su contenido).
    
    Args:
        output_dir: Path del directorio a limpiar
        silent: Si es True, no pide confirmación (ya se pidió en GUI)
    """
    if output_dir.exists():
        if not silent:
            print(f"\n⚠️  ADVERTENCIA: El directorio de salida existe y será limpiado:")
            print(f"    {output_dir.absolute()}")
            print(f"\n    Se eliminarán TODOS los archivos y subdirectorios.")
            
            response = input("\n¿Continuar? (s/N): ").strip().lower()
            
            if response not in ('s', 'si', 'sí', 'y', 'yes'):
                print("\nOperación cancelada por el usuario.")
                sys.exit(0)
        
        print(f"\nLimpiando directorio de salida...", end=' ')
        
        # Eliminar todo el contenido
        for item in output_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        
        print("✓")


def process_ls_file(input_path, output_path):
    """
    Procesa un archivo .ls añadiendo IDs de soldadura a los puntos.
    
    Args:
        input_path: Ruta del archivo de entrada
        output_path: Ruta del archivo de salida
        
    Returns:
        dict: Estadísticas del procesamiento
    """
    with open(input_path, 'r', encoding='latin-1') as f:
        lines = f.readlines()
    
    point_modifications = {}
    modified_lines = []
    changes_mn = 0
    skipped_mn = 0
    
    # ========================================================================
    # PASO 1: Procesar bloque /MN
    # ========================================================================
    in_mn_block = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar inicio de bloque /MN
        if line.strip() == '/MN':
            in_mn_block = True
            modified_lines.append(line)
            i += 1
            continue
        
        # Detectar fin de bloque /MN
        if in_mn_block and line.strip().startswith('/') and line.strip() != '/MN':
            in_mn_block = False
        
        # Procesar líneas dentro del bloque /MN
        if in_mn_block:
            # Buscar patrón: *:!T*-XXXXX ;
            match_comment = re.search(r'\d+\s*:\s*!\s*T.*-(\d+)\s*;', line)
            
            if match_comment and i + 1 < len(lines):
                spot_id = match_comment.group(1)
                next_line = lines[i + 1]
                
                # Buscar patrón: L/J P[*] *mm/sec CNT*
                match_movement = re.search(r'(\d+\s*:)?\s*([LJ])\s+P\s*\[\s*(\d+)\s*\]', next_line)
                
                if match_movement:
                    point_num = match_movement.group(3)
                    
                    # IMPORTANTE: Verificar si ya tiene ":" en P[...]
                    if ':' in re.search(r'P\s*\[([^\]]+)\]', next_line).group(1):
                        # Ya está modificado, no hacer nada
                        modified_lines.append(line)
                        modified_lines.append(next_line)
                        skipped_mn += 1
                        i += 2
                        continue
                    
                    # No tiene ":", proceder con la modificación
                    point_modifications[point_num] = spot_id
                    
                    modified_next_line = re.sub(
                        r'P\s*\[\s*' + point_num + r'\s*\]',
                        f'P[{point_num}:{spot_id}]',
                        next_line
                    )
                    
                    modified_lines.append(line)
                    modified_lines.append(modified_next_line)
                    changes_mn += 1
                    
                    i += 2
                    continue
        
        modified_lines.append(line)
        i += 1
    
    # ========================================================================
    # PASO 2: Procesar bloque /POS
    # ========================================================================
    in_pos_block = False
    final_lines = []
    changes_pos = 0
    skipped_pos = 0
    
    for line in modified_lines:
        # Detectar inicio de bloque /POS
        if line.strip() == '/POS':
            in_pos_block = True
            final_lines.append(line)
            continue
        
        # Detectar fin de bloque /POS
        if in_pos_block and line.strip().startswith('/') and line.strip() != '/POS':
            in_pos_block = False
        
        # Procesar líneas dentro del bloque /POS
        line_modified = False
        if in_pos_block:
            for point_num, spot_id in point_modifications.items():
                # Buscar patrón: P[num]{
                pattern = r'P\s*\[\s*' + point_num + r'\s*\]\s*\{'
                
                if re.search(pattern, line):
                    # IMPORTANTE: Verificar si ya tiene ":" en P[...]
                    match_bracket = re.search(r'P\s*\[([^\]]+)\]', line)
                    if match_bracket and ':' in match_bracket.group(1):
                        # Ya está modificado, no hacer nada
                        final_lines.append(line)
                        skipped_pos += 1
                        line_modified = True
                        break
                    
                    # No tiene ":", proceder con la modificación
                    modified_line = re.sub(
                        r'P\s*\[\s*' + point_num + r'\s*\]\s*(\{)',
                        f'P[{point_num}:"{spot_id}"]\\1',
                        line
                    )
                    
                    final_lines.append(modified_line)
                    changes_pos += 1
                    line_modified = True
                    break
        
        if not line_modified:
            final_lines.append(line)
    
    # Guardar archivo modificado
    with open(output_path, 'w', encoding='latin-1') as f:
        f.writelines(final_lines)
    
    return {
        'changes_mn': changes_mn,
        'changes_pos': changes_pos,
        'skipped_mn': skipped_mn,
        'skipped_pos': skipped_pos
    }


def main():
    """
    Función principal del script.
    Soporta dos modos:
    - Sin argumentos: interfaz gráfica
    - Con argumentos: línea de comandos
    """
    # Determinar modo de operación
    use_gui = len(sys.argv) == 1
    
    if use_gui:
        # ====================================================================
        # MODO INTERFAZ GRÁFICA
        # ====================================================================
        print("=" * 70)
        print("PROCESAMIENTO DE ARCHIVOS .LS - MODO INTERFAZ GRÁFICA")
        print("=" * 70)
        print("\nIniciando selector de directorios...")
        
        input_dir_str, output_dir_str = select_directories_gui()
        
        if input_dir_str is None or output_dir_str is None:
            sys.exit(0)
        
        input_dir = Path(input_dir_str)
        output_dir = Path(output_dir_str)
        silent_mode = True  # Ya se confirmó en la GUI
        
    else:
        # ====================================================================
        # MODO LÍNEA DE COMANDOS
        # ====================================================================
        # Verificar argumentos
        if len(sys.argv) != 3:
            print("Error: Número incorrecto de argumentos")
            print()
            print("Uso:")
            print(f"    # Modo interfaz gráfica (recomendado):")
            print(f"    python {sys.argv[0]}")
            print()
            print(f"    # Modo línea de comandos:")
            print(f"    python {sys.argv[0]} <directorio_entrada> <directorio_salida>")
            print()
            print("Ejemplo:")
            print(f"    python {sys.argv[0]}")
            print(f"    python {sys.argv[0]} ./programas_originales ./programas_modificados")
            sys.exit(1)
        
        input_dir = Path(sys.argv[1])
        output_dir = Path(sys.argv[2])
        silent_mode = False
        
        # Verificar que el directorio de entrada existe
        if not input_dir.exists():
            print(f"Error: El directorio de entrada no existe: {input_dir}")
            sys.exit(1)
        
        if not input_dir.is_dir():
            print(f"Error: La ruta de entrada no es un directorio: {input_dir}")
            sys.exit(1)
    
    # ========================================================================
    # PROCESAMIENTO (común para ambos modos)
    # ========================================================================
    
    # Limpiar directorio de salida
    clean_output_directory(output_dir, silent=silent_mode)
    
    # Crear directorio de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Buscar archivos .ls recursivamente
    ls_files = list(input_dir.rglob('*.ls'))
    
    if not ls_files:
        msg = f"No se encontraron archivos .ls en: {input_dir}"
        print(msg)
        if use_gui:
            root = Tk()
            root.withdraw()
            messagebox.showinfo("Sin archivos", msg)
            root.destroy()
        sys.exit(0)
    
    print("=" * 70)
    print("PROCESAMIENTO DE ARCHIVOS .LS - MODIFICACIÓN DE PUNTOS DE SOLDADURA")
    print("=" * 70)
    print(f"\nDirectorio entrada: {input_dir.absolute()}")
    print(f"Directorio salida:  {output_dir.absolute()}")
    print(f"Archivos encontrados: {len(ls_files)}")
    print()
    
    # Procesar cada archivo
    total_changes_mn = 0
    total_changes_pos = 0
    total_skipped_mn = 0
    total_skipped_pos = 0
    results = []
    
    for input_file in sorted(ls_files):
        # Calcular la ruta relativa desde el directorio de entrada
        relative_path = input_file.relative_to(input_dir)
        
        # Crear la misma estructura de directorios en el output
        output_file = output_dir / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Mostrar la ruta relativa para mejor legibilidad
        display_path = str(relative_path).replace('\\', '/')
        print(f"Procesando: {display_path}...", end=' ')
        
        try:
            stats = process_ls_file(input_file, output_file)
            
            total_changes_mn += stats['changes_mn']
            total_changes_pos += stats['changes_pos']
            total_skipped_mn += stats['skipped_mn']
            total_skipped_pos += stats['skipped_pos']
            
            print(f"✓ /MN:{stats['changes_mn']:3} /POS:{stats['changes_pos']:3}", end='')
            
            if stats['skipped_mn'] > 0 or stats['skipped_pos'] > 0:
                print(f" (omitidos: {stats['skipped_mn'] + stats['skipped_pos']})", end='')
            
            print()
            
            results.append({
                'archivo': display_path,
                'modificados': stats['changes_mn'] + stats['changes_pos'],
                'omitidos': stats['skipped_mn'] + stats['skipped_pos'],
                'estado': 'OK'
            })
            
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results.append({
                'archivo': display_path,
                'modificados': 0,
                'omitidos': 0,
                'estado': f'ERROR: {str(e)[:30]}'
            })
    
    # Resumen final
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"\nArchivos procesados: {len(ls_files)}")
    print(f"Total modificaciones /MN:  {total_changes_mn}")
    print(f"Total modificaciones /POS: {total_changes_pos}")
    
    if total_skipped_mn > 0 or total_skipped_pos > 0:
        print(f"Total omitidos (ya modificados): {total_skipped_mn + total_skipped_pos}")
    
    print()
    print("Archivos guardados en:", output_dir.absolute())
    print("✓ Estructura de directorios reproducida correctamente")
    print()
    
    # Mostrar mensaje final en GUI
    if use_gui:
        summary_msg = (
            f"✓ PROCESAMIENTO COMPLETADO\n\n"
            f"Archivos procesados: {len(ls_files)}\n"
            f"Modificaciones totales: {total_changes_mn + total_changes_pos}\n"
        )
        
        if total_skipped_mn > 0 or total_skipped_pos > 0:
            summary_msg += f"Archivos omitidos (ya modificados): {total_skipped_mn + total_skipped_pos}\n"
        
        summary_msg += f"\nArchivos guardados en:\n{output_dir.absolute()}"
        
        root = Tk()
        root.withdraw()
        messagebox.showinfo("Procesamiento Completado", summary_msg)
        root.destroy()


if __name__ == '__main__':
    main()
