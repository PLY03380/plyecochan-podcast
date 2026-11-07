import tempfile
import shutil
import subprocess
from pathlib import Path
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

slides = sorted(Path('output/visuels/2026-10-15').glob('slide*_devise.png'))
audio = Path('output/audio/2026-10-15/narration_en.mp3')
slide_duration = 6.0

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    audio_dst = tmp / 'audio.mp3'
    shutil.copy(audio, audio_dst)
    
    slide_videos = []
    for i, slide in enumerate(slides):
        slide_vid = tmp / f'slide_vid_{i}.mp4'
        frames = int(round(slide_duration * 30))
        
        for f in range(frames):
            frame_f = tmp / f'slide{i}_frame_{f:04d}.png'
            shutil.copy(slide, frame_f)
        
        cmd = [FFMPEG, '-y', '-framerate', '30', '-i', str(tmp / f'slide{i}_frame_%04d.png'),
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', str(slide_vid)]
        subprocess.run(cmd, capture_output=True)
        
        for f in tmp.glob(f'slide{i}_frame_*.png'):
            f.unlink()
        slide_videos.append(slide_vid)
    
    for sv in slide_videos:
        result = subprocess.run([FFMPEG, '-i', str(sv), '-f', 'null', '-'], capture_output=True, text=True)
        import re
        match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)', result.stderr)
        if match:
            h, m, s = match.groups()
            print(f'  {sv.name}: {int(h)*3600 + int(m)*60 + float(s):.1f}s')
    
    list_file = tmp / 'concat_list.txt'
    lines = []
    for v in slide_videos:
        lines.append("file '" + v.name + "'\n")
    list_file.write_text(''.join(lines), encoding='utf-8')
    
    out_tmp = tmp / 'out.mp4'
    cmd = [FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
           '-i', str(audio_dst), '-map', '0:v', '-map', '1:a',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
           '-c:a', 'aac', '-b:a', '128k', '-shortest',
           '-movflags', '+faststart', '-pix_fmt', 'yuv420p', str(out_tmp)]
    subprocess.run(cmd, capture_output=True, cwd=tmp)
    
    result = subprocess.run([FFMPEG, '-i', str(out_tmp), '-f', 'null', '-'], capture_output=True, text=True)
    match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)', result.stderr)
    if match:
        h, m, s = match.groups()
        print(f'Final: {int(h)*3600 + int(m)*60 + float(s):.1f}s')