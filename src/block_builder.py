import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

REQUIRED_KEYS = {"code", "color", "name", "typeName", "palette", "type", "spec"}
VALID_TYPES = {"h", " ", "b", "d", "f", "c", "l", "s", "v", "a"}


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {
            "sketchware_version": "7.0 PRO",
            "default_sketchware_path": "/storage/emulated/0/.sketchware",
            "backup_dir": "./backups",
        }
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_blocks(data: object) -> list[str]:
    errors = []
    if not isinstance(data, list) or len(data) == 0:
        return ["O JSON raiz deve ser uma lista (array) não vazia de blocos."]

    for idx, block in enumerate(data):
        if not isinstance(block, dict):
            errors.append(f"Item [{idx}]: deve ser um objeto JSON.")
            continue
        missing = REQUIRED_KEYS - set(block.keys())
        if missing:
            errors.append(f"Item [{idx}] ({block.get('name', 'sem nome')}): faltam campos {sorted(missing)}.")
        if "type" in block and block["type"] not in VALID_TYPES:
            errors.append(
                f"Item [{idx}] ({block.get('name', 'sem nome')}): tipo '{block['type']}' incomum para Sketchware PRO 7.0."
            )
    return errors


def build_json(input_file: Path, output_file: Path, minify: bool = False) -> None:
    with input_file.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    errors = validate_blocks(raw_data)
    if errors:
        raise ValueError("Falha na validação do JSON:\n- " + "\n- ".join(errors))

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        if minify:
            json.dump(raw_data, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {len(raw_data)} bloco(s) validado(s) e salvo(s) em: {output_file}")


def sync_to_sketchware(source_file: Path, sw_path: str, backup_root: str) -> None:
    target_dir = Path(sw_path)
    if not target_dir.exists():
        print(f"[AVISO] Diretório do Sketchware não encontrado em: {target_dir}")
        print("[DICA] Em Android/Termux, verifique se o armazenamento está liberado (termux-setup-storage).")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_root) / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, backup_dir / source_file.name)

    dest_file = target_dir / source_file.name
    shutil.copy2(source_file, dest_file)
    print(f"[OK] Backup criado em: {backup_dir / source_file.name}")
    print(f"[OK] Arquivo enviado para: {dest_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sketchware PRO 7.0 Block Builder CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_cmd = subparsers.add_parser("build", help="Valida e gera o JSON de blocos")
    validate_cmd.add_argument("-i", "--input", required=True, help="Caminho do JSON de entrada")
    validate_cmd.add_argument("-o", "--output", required=True, help="Caminho do JSON de saída")
    validate_cmd.add_argument("--minify", action="store_true", help="Gera JSON em linha única")

    sync_cmd = subparsers.add_parser("sync", help="Faz backup e copia o JSON para o diretório do Sketchware")
    sync_cmd.add_argument("-f", "--file", required=True, help="Arquivo JSON já validado")
    sync_cmd.add_argument("--sw-path", default=None, help="Sobrescreve o path padrão (/storage/emulated/0/.sketchware)")

    args = parser.parse_args()
    config = load_config(Path("config/sketchware_pro7.json"))

    if args.command == "build":
        build_json(Path(args.input), Path(args.output), minify=args.minify)
    elif args.command == "sync":
        sw_path = args.sw_path or config.get("default_sketchware_path", "/storage/emulated/0/.sketchware")
        backup_dir = config.get("backup_dir", "./backups")
        sync_to_sketchware(Path(args.file), sw_path, backup_dir)


if __name__ == "__main__":
    main()
