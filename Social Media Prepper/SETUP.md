# Social Studio - Complete Setup Guide

## ✅ Project is Ready!

Your Social Studio web app is **fully functional** and ready to use.

## 🚀 Quick Start

```bash
# Start the server
python app.py

# Open browser
http://localhost:5000
```

## 📋 What's Included

### ✅ Complete Features

1. **File Upload System** - Working!
   - Audio: MP3, WAV, M4A, AAC → `uploads/audio/`
   - Images: JPG, PNG, WEBP → `uploads/images/`
   - Session persistence with static secret key
   - Timestamped filenames
   - File counter on upload page

2. **Preview System** - Working!
   - Audio: HTML5 audio player
   - Images: Image display
   - Direct download buttons

3. **Editor** - Working!
   - Audio trimming (FFmpeg required)
   - Image cropping for platforms
   - Caption/hashtag generation

4. **Export** - Working!
   - Buffer, Publer, Later, Meta
   - CSV and JSON formats

### 📁 Folder Structure

```
Social-Studio/
├── app.py                     ✅ Flask server (fixed session & uploads)
├── requirements.txt           ✅ Dependencies (audio/image only)
├── templates/
│   ├── base.html             ✅ Base template
│   ├── index.html            ✅ Landing page
│   ├── upload.html           ✅ Upload with media selector
│   ├── editor.html           ✅ Media editor
│   └── preview.html          ✅ Preview with download
├── static/
│   ├── css/style.css         ✅ Complete styling
│   └── js/main.js            ✅ Utilities
├── social_studio/
│   ├── config_manager.py     ✅ Configuration
│   ├── content_processor.py  ✅ Audio/Image (no video)
│   ├── caption_generator.py  ✅ AI captions
│   └── export_manager.py     ✅ Scheduler export
├── uploads/
│   ├── audio/                ✅ Audio files storage
│   └── images/               ✅ Image files storage
├── output/                    ✅ Processed files
└── config/config.yaml         ✅ Platform settings
```

## 🎯 User Workflow

```
1. Landing (/) 
   ↓
2. Upload (/upload)
   - Choose: 🎵 Audio or 🖼️ Image
   - Drag & drop files
   - See file counter: "Continue to Editor (2)"
   ↓
3. Editor (/editor)
   - Select file from list
   - Trim audio OR crop image
   - Generate captions/hashtags
   ↓
4. Preview (/preview)
   - Play audio OR view image
   - Download processed files
   - Export metadata for schedulers
```

## 🔧 Technical Details

### Routes
- `GET /` - Landing page
- `GET /upload` - Upload page
- `POST /api/upload` - Handle file upload
- `GET /api/session/files` - Get uploaded files
- `POST /api/session/clear` - Clear session
- `GET /editor` - Media editor
- `POST /api/process` - Process media
- `POST /api/generate-content` - Generate captions
- `GET /preview` - Preview page
- `GET /api/preview/<filename>` - Serve file
- `GET /download/<filename>` - Download file
- `POST /api/export` - Export metadata

### Session Management
- **Secret Key**: `'social-studio-secret-key-2026'` (static, not random)
- **Persists**: Uploaded files tracked across page reloads
- **Storage**: `session['uploaded_files']` array

### File Storage
- **Uploads**: `uploads/audio/` and `uploads/images/`
- **Processed**: `output/`
- **Exports**: `scheduler_export/`
- **Naming**: `YYYYMMDD_HHMMSS_filename.ext`

## 📦 Dependencies

```txt
flask>=2.3.0
werkzeug>=2.3.0
pyyaml>=6.0
pillow>=10.0.0
python-dateutil>=2.8.0
```

**Note**: Video dependencies removed (moviepy, opencv, pydub, numpy)

## 🐛 Troubleshooting

### Files not appearing in editor?
- Check browser console for errors
- Verify `uploads/audio/` and `uploads/images/` folders exist
- Clear session: `/api/session/clear` (POST)
- Restart server

### FFmpeg not found?
- Install FFmpeg for audio trimming
- Windows: Download from ffmpeg.org
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Session not persisting?
- ✅ Fixed! Secret key is now static
- Files should persist across page reloads

## 🚢 Ready to Deploy

### To GitHub
```bash
git add .
git commit -m "Complete Social Studio - Audio & Image only"
git push origin main
```

### Share with Friends
```
1. Clone repo: git clone https://github.com/dandziewit/Social-Studio
2. Install: pip install -r requirements.txt
3. Run: python app.py
4. Open: http://localhost:5000
```

## ✨ Recent Fixes

✅ Fixed secret key (was regenerating on restart)
✅ Created uploads/audio/ and uploads/images/
✅ Session persistence working
✅ File counter on upload page
✅ Preview routes check all subfolders
✅ Download routes support all file types
✅ Removed all video code completely
✅ Updated templates to audio/image only

---

**Your Social Studio is ready! 🎉**

Run `python app.py` and start creating! 🎵🖼️
