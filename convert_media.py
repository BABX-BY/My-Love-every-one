from pathlib import Path
import subprocess
from PIL import Image
from pillow_heif import register_heif_opener
import imageio_ffmpeg

register_heif_opener()
root = Path(__file__).resolve().parent
all_dir = root / 'All'
converted_dir = all_dir / 'converted'
converted_dir.mkdir(exist_ok=True)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
print('ffmpeg exe:', ffmpeg)
files = sorted([p for p in all_dir.iterdir() if p.is_file()])
converted_images = 0
converted_videos = 0
skipped_images = 0
skipped_videos = 0
failed = []

for p in files:
    ext = p.suffix.lower()
    
    # --- จัดการรูปภาพ (ย่อขนาดและบีบอัด) ---
    if ext == '.heic' or ext in ['.jpg', '.jpeg', '.png']: # รองรับรูปทั่วไปด้วย
        out = converted_dir / (p.stem + '.jpg')
        if out.exists() and out.stat().st_mtime >= p.stat().st_mtime:
            skipped_images += 1
            continue
        try:
            img = Image.open(p)
            img = img.convert('RGB')
            # ลดขนาดรูปให้กว้าง/ยาวสุดไม่เกิน 1080px 
            img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
            # เซฟเป็น JPEG แบบบีบอัด (ลดขนาดไฟล์ได้มหาศาล)
            img.save(out, format='JPEG', quality=75)
            converted_images += 1
            print('converted image', p.name)
        except Exception as e:
            failed.append((p.name, 'image', str(e)))
            
    # --- จัดการวิดีโอ (ลดความละเอียดเป็น 720p และบีบอัด) ---
    elif ext in ['.mov', '.mp4']:
        out = converted_dir / (p.stem + '.mp4')
        force_reencode = True
        if out.exists() and out.stat().st_mtime >= p.stat().st_mtime and not force_reencode:
            skipped_videos += 1
            continue
            
        cmd = [
            ffmpeg,
            '-y',
            '-i', str(p),
            '-vf', 'scale=-2:720',  # บังคับย่อวิดีโอให้ความสูงเหลือ 720p (ความกว้างปรับตามอัตโนมัติ)
            '-c:v', 'libx264',
            '-preset', 'fast',      # ทำให้แปลงไฟล์เร็วขึ้น
            '-crf', '28',           # เลขยิ่งเยอะ ไฟล์ยิ่งเล็ก (28 คือกำลังดี ไม่แตกเกินไป)
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',         # บีบอัดเสียงด้วย
            '-movflags', '+faststart',
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            failed.append((p.name, 'video', proc.stderr.strip().splitlines()[-1] if proc.stderr else 'unknown error'))
            print('FAILED', p.name)
        else:
            converted_videos += 1
            print('converted video', p.name)

print('\n--- สรุปผลการแปลงไฟล์ ---')
print('converted_images', converted_images)
print('skipped_images', skipped_images)
print('converted_videos', converted_videos)
print('skipped_videos', skipped_videos)
print('failed_count', len(failed))
for item in failed[:20]:
    print(item)