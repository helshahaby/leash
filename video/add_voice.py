"""Add a voiceover + music bed to leash-demo.mp4.
Usage (Windows PowerShell):  $env:ELEVEN_API_KEY="..."; python add_voice.py
Never paste your key into a chat. Needs ffmpeg + ffprobe on PATH and `pip install requests`.
Safe to re-run: clips already generated (seg*.mp3) are reused, so re-runs cost no quota.
Env: ELEVEN_VOICE_ID, ELEVEN_MODEL. Set MOCK=1 to test the audio pipeline with beeps (no API call).
Set TTS=local to use free offline voices via `pip install pyttsx3` (no quota)."""
import os, re, subprocess, sys
SEGS = [
 (0.2, 4.6, "AI agents can pay for things now. Would you hand one your private key?"),
 (5.2, 6.6, "Leash gives it a budget instead: ten cents per payment, a dollar a day, one approved merchant."),
 (12.3, 11.4, "The agent pays two cents for an API call, and gets its data in about a second."),
 (24.3, 11.4, "Now it's hijacked, and told to send four dollars to a stranger. The program refuses. Every time."),
 (36.3, 4.5, "One transaction revokes the agent completely."),
 (41.2, 3.6, "Leash. Give your agent a budget, not your wallet."),
]
def run(*a): return subprocess.run(a, capture_output=True, text=True)
def dur(p): return float(run("ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p).stdout.strip() or 0)
def mean_db(p):
    r = run("ffmpeg","-i",p,"-af","volumedetect","-vn","-f","null","-")
    m = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", r.stderr)
    return float(m.group(1)) if m and m.group(1) != "-inf" else -99.0
def make_clip(i, text, out):
    mode = os.environ.get("TTS","eleven")
    if os.environ.get("MOCK"):
        run("ffmpeg","-y","-f","lavfi","-i",f"sine=frequency={300+60*i}:duration=3","-c:a","libmp3lame",out); return
    if mode == "local":
        import pyttsx3; e = pyttsx3.init(); e.setProperty("rate", 175)
        wav = out.replace(".mp3",".wav"); e.save_to_file(text, wav); e.runAndWait()
        run("ffmpeg","-y","-i",wav,"-c:a","libmp3lame",out); return
    import requests
    voice = os.environ.get("ELEVEN_VOICE_ID","JBFqnCBsd6RMkjVDRZzb"); model = os.environ.get("ELEVEN_MODEL","eleven_multilingual_v2")
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        headers={"xi-api-key":os.environ["ELEVEN_API_KEY"]}, json={"text":text,"model_id":model}, timeout=90)
    ctype = r.headers.get("content-type","")
    if r.status_code != 200 or "audio" not in ctype:
        sys.exit(f"ElevenLabs error {r.status_code} ({ctype}): {r.text[:300]}")
    open(out,"wb").write(r.content)
inputs, filt, labels = ["-i","leash-demo.mp4","-i","music.wav"], [], []
for i,(start,win,text) in enumerate(SEGS):
    f = f"seg{i}.mp3"
    if not (os.path.exists(f) and os.path.getsize(f) > 4000 and mean_db(f) > -60):
        make_clip(i, text, f)
    d, db = dur(f), mean_db(f)
    print(f"seg{i}: {os.path.getsize(f)} bytes, {d:.1f}s, mean volume {db} dB")
    if d < 0.5 or db < -60: sys.exit(f"seg{i}.mp3 is silent or empty. Delete it and re-run, or check the voice id / quota.")
    tempo = min(1.6, max(1.0, d/win)); inputs += ["-i", f]
    ms = int(start*1000)
    filt.append(f"[{i+2}:a]aformat=sample_rates=44100:channel_layouts=stereo,atempo={tempo:.3f},adelay={ms}|{ms}[v{i}]"); labels.append(f"[v{i}]")
filt.append("".join(labels)+f"amix=inputs={len(SEGS)}:normalize=0:duration=longest[voice]")
filt.append("[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.22[m];[voice][m]amix=inputs=2:normalize=0:duration=longest,asetpts=N/SR/TB[a]")
# Step 1: render the audio mix to a WAV (avoids encoder timestamp problems), Step 2: mux it in.
ain = [x for x in inputs if x != "leash-demo.mp4"]; ain = ain[1:]  # drop the first "-i leash-demo.mp4"
fc = ";".join(filt).replace("[1:a]", "[0:a]")
for k in range(len(SEGS)):  # input indexes shift by one without the video input
    fc = fc.replace(f"[{k+2}:a]", f"[{k+1}:a]")
r = run("ffmpeg","-y",*ain,"-filter_complex",fc,"-map","[a]","-ar","44100","-ac","2","-t","45","mix.wav")
if r.returncode: sys.exit(r.stderr[-1500:])
print(f"mix.wav: {dur('mix.wav'):.1f}s, mean volume {mean_db('mix.wav')} dB")
if dur("mix.wav") < 40 or mean_db("mix.wav") < -60: sys.exit("The audio mix is silent or too short. Send me the lines printed above.")
r = run("ffmpeg","-y","-i","leash-demo.mp4","-i","mix.wav","-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","leash-demo-final.mp4")
if r.returncode: sys.exit(r.stderr[-1500:])
ad = run("ffprobe","-v","error","-select_streams","a","-show_entries","stream=duration","-of","csv=p=0","leash-demo-final.mp4").stdout.strip()
print(f"leash-demo-final.mp4: audio {ad}s, mean volume {mean_db('leash-demo-final.mp4')} dB. Audio should be about 45s and above -60 dB.")