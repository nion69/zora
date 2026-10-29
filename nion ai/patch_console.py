import re
import json
from pathlib import Path

path = r'G:\tools\nionai assistant\nion ai\nion ai\agent.py'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

new_setup_audio = '''def setup_audio_devices():
    try:
        import sounddevice as sd
        devices = sd.query_devices()

        cfg_file = Path.home() / ".zoraai" / "config.json"
        saved_mic = None
        saved_spk = None
        if cgf_file.exists():
            try:
                cfg_data = json.loads(cgf_file.read_text(encoding="utf-8"))
                saved_mic = cfg_data.get("input_device")
                saved_spk = cfg_data.get("output_device")
            except Exception:
                pass

        current_in, current_out = sd.default.device
        target_in = saved_mic if saved_mic is not None and 0 <= saved_mic < len(devices) else get_best_microphone_index()
        target_out = saved_spk if saved_spk is not None and 0 <= saved_spk < len(devices) else current_out

        if target_in is not None:
            sd.default.device = (target_in, target_out if target_out is not None else current_out)
            mic_name = devices[target_in]['name']
            spk_name = devices[target_out]['name'] if target_out is not None else "Default"
            print(f"[Zora Audio] Selected Audio Devices -> Mic: [{target_in}] {mic_name} | Speaker: [{target_out}] {spk_name}")
            return target_in, target_out
    except Exception as e:
        print(f"[Zora Audio] Mic setup note: {e}")
    return None, None'''

pattern_setup = r'def setup_audio_devices\(\):[\s\S]*?(?=def get_best_microphone_index|setup_audio_devices\(	\n |import sys)'
code = re.sub(pattern_setup, new_setup_audio + '\n'+'setup_audio_devices()\n', code, count=1)

new_console = '''    elif cmd == "console":
        sel_mic, sel_spk = setup_audio_devices()
        _print_zora_banner("CONSOLE", "Interactive Console Mode (PC Mic & Speakers active)")
        print("  Speak into your microphone. Press Ctrl+C to stop.\n")
        cmd_args = ["zora", "console"]
        if sel_mic is not None:
            cmd_args.extend(["--input-device", str(sel_mic)])
        if sel_spk is not None:
            cmd_args.extend(["--output-device", str(sel_spk)])
        sys.argv = cmd_args
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))'''

pattern_console = r'\s*elif cmd == "console":l\s\S]*?(?=else:)'
match = re.search(pattern_console, code)
if match:
    code = re.sub(pattern_console, new_console + '\n'+'    ', code)

with open(path, 'w', encoding='utf-8') as f:
    f.write(code)
print('CONSOLE_PATCHED_SUCCESS' if match else 'FC_NOT_MATCHED')
