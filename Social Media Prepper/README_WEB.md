# Social Studio - Web Version

**Browser-based Social Media Content Creator** 

Create, edit, and export professional social media content directly in your browser. No Streamlit required - runs as a standalone Flask web application.

## 🌐 Features

- **Web-Based Interface**: Access from any modern browser
- **File Upload**: Drag & drop audio, video, and images
- **Real-Time Editing**: Trim audio, crop images, edit videos
- **AI Content Generation**: Auto-generated captions and hashtags
- **Multi-Platform Support**: Instagram, TikTok, Facebook, YouTube, Twitter
- **Scheduler Export**: Export to Buffer, Publer, Later, Meta Business Suite

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- FFmpeg installed on your system

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/dandziewit/Social-Studio.git
cd Social-Studio
```

2. **Install Python dependencies:**
```bash
pip install -r requirements_web.txt
```

3. **Run the web app:**
```bash
python app_web.py
```

4. **Open in browser:**
Navigate to `http://localhost:5000`

## 📁 Project Structure

```
social-studio-web/
├── app_web.py              # Flask application entry point
├── requirements_web.txt    # Python dependencies
├── config/
│   └── config.yaml         # Configuration
├── templates/              # HTML templates
│   ├── base.html          # Base template
│   ├── index.html         # Home page
│   ├── upload.html        # File upload
│   ├── editor.html        # Media editor
│   └── preview.html       # Preview & export
├── static/                 # Static assets
│   ├── css/
│   │   └── style.css      # Styles
│   └── js/
│       └── main.js        # JavaScript
├── social_studio/          # Core Python modules
│   ├── config_manager.py
│   ├── content_processor.py
│   ├── caption_generator.py
│   └── export_manager.py
└── uploads/                # Uploaded files (auto-created)
```

## 🎯 Usage

### 1. Upload Media
- Go to Upload page
- Drag & drop or click to select files
- Supports: MP3, WAV, MP4, JPG, PNG

### 2. Edit Content
- Select files in the editor
- Trim audio clips (set start time and duration)
- Crop images (choose aspect ratio)
- Generate captions and hashtags

### 3. Preview & Export
- Review processed content
- Select scheduler (Buffer, Publer, Later, Meta)
- Choose export format (CSV or JSON)
- Download ready-to-post content

## 🔧 Configuration

Edit `config/config.yaml` to customize:

```yaml
platforms:
  instagram:
    enabled: true
    max_duration: 60
  tiktok:
    enabled: true
    max_duration: 60

caption_templates:
  default:
    - "Check this out! 🎬"
    - "New content alert! 🔥"

hashtag_sets:
  general:
    - "#content"
    - "#creative"
```

## 🌐 Deployment

### Deploy to Heroku

1. **Create Heroku app:**
```bash
heroku create your-social-studio
```

2. **Add buildpacks:**
```bash
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
heroku buildpacks:add --index 2 heroku/python
```

3. **Create Procfile:**
```
web: gunicorn app_web:app
```

4. **Deploy:**
```bash
git push heroku main
```

### Deploy to PythonAnywhere

1. Upload files to PythonAnywhere
2. Create a new web app (Flask)
3. Set WSGI file to point to `app_web.py`
4. Install requirements: `pip install -r requirements_web.txt`
5. Reload web app

### Deploy to GitHub Pages (with backend)

The web interface can be hosted on GitHub Pages, but you'll need a separate backend server for file processing. Consider:
- AWS Lambda for processing
- Heroku for Flask backend
- Firebase Functions

## 📦 API Endpoints

### Upload
- `POST /api/upload` - Upload media file
- Returns: `{success: true, filename: '...', type: '...'}`

### Process
- `POST /api/process` - Process media (trim/crop)
- Body: `{file: {...}, start_time: 0, duration: 15}`

### Generate Content
- `POST /api/generate-content` - Generate captions/hashtags
- Body: `{platform: 'instagram', media_type: 'image'}`

### Export
- `POST /api/export` - Export for schedulers
- Body: `{posts: [...], scheduler: 'buffer', format: 'csv'}`

### Download
- `GET /download/<filename>` - Download processed file

## 🛠️ Development

### Run in debug mode:
```bash
python app_web.py
# App runs on http://localhost:5000 with auto-reload
```

### Run tests:
```bash
python -m pytest tests/
```

### Code formatting:
```bash
black app_web.py social_studio/
```

## 📝 Requirements

### System Requirements
- Python 3.10+
- FFmpeg (for audio/video processing)
- 2GB+ RAM recommended

### Python Packages
- Flask 2.3+
- Pillow 10.0+
- PyYAML 6.0+
- pydub, moviepy, numpy, opencv-python

## 🔒 Security Notes

- Files are temporarily stored in `uploads/` folder
- Session data is stored server-side
- Maximum upload size: 50MB per file
- Files are automatically cleaned up after processing

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file

## 👤 Author

**Damiel Dziewit**
- GitHub: [@dandziewit](https://github.com/dandziewit)

## 🆘 Support

For issues or questions:
- Open an issue on GitHub
- Check documentation in `docs/` folder

---

**Made for content creators, by a content creator** ❤️
