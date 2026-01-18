# 🎯 Social Studio - Complete Feature Guide

## ✨ Auto-Generated Content

### 🤖 Caption Generation
- **Automatic on Upload**: Every file uploaded automatically gets a caption
- **Platform-Specific**: Captions tailored for Instagram, TikTok, YouTube
- **Editable**: All auto-generated captions can be customized
- **Character Counter**: Real-time character count for platform limits

### 🏷️ Hashtag Generation
- **Auto-Generated**: Hashtags created for each file based on content type
- **Customizable**: Add, remove, or regenerate hashtags
- **Visual Tags**: Hashtags displayed as colorful badges
- **One-Click Regenerate**: Refresh hashtags with a single click

---

## 📁 File Upload System

### Supported Formats
- **Audio**: MP3, WAV, M4A, AAC
- **Images**: JPG, JPEG, PNG, WEBP

### Smart Upload
- **Drag & Drop**: Drop files directly into the upload zone
- **Multiple Files**: Upload multiple files at once
- **Auto-Detection**: Automatically determines audio vs image
- **Progress Indicator**: Real-time upload progress
- **Caption Preview**: See auto-generated captions right after upload

### Session Management
- Files persist across page reloads
- Continue button appears after first upload
- File counter shows total uploaded files
- Clear all button to start fresh

---

## ✏️ Enhanced Editor

### Per-File Editing
- **Individual File View**: Edit each file separately
- **Caption Editor**: Full-featured text editor with character count
- **Hashtag Manager**: 
  - Add hashtags with input field
  - Remove hashtags by clicking on them
  - Regenerate all hashtags instantly
  - Visual hashtag badges

### Audio Editing
- **Trim Tool**: Set start time and duration
- **Precision Control**: Decimal precision (e.g., 10.5 seconds)
- **Preview Before Export**: Test your trim settings
- **Platform Presets**: Quick settings for Reels (15s), TikTok (60s)

### Image Editing
- **Smart Crop**: Automatic cropping to platform specs
- **Aspect Ratios**:
  - 1:1 (Square - Instagram Feed)
  - 9:16 (Story - Instagram/TikTok)
  - 4:5 (Portrait - Instagram)
  - 16:9 (Landscape - YouTube Thumbnail)
- **One-Click Apply**: Crop and process instantly

### Editor Features
- **Auto-Save**: Changes automatically saved to session
- **File Switcher**: Easy navigation between files
- **Visual Indicators**: Active file highlighting
- **Empty State**: Helpful prompts when no files selected

---

## 👀 Preview & Export

### Preview Mode
- **Audio Player**: HTML5 audio player for immediate playback
- **Image Display**: Full-size image preview
- **Caption Display**: See captions and hashtags
- **Download Individual**: Download each file separately

### Export Options

#### 📥 Individual Downloads
- Download any file with a single click
- Files include all applied edits
- Original filenames preserved

#### 📦 ZIP Export (NEW!)
- **One-Click Download**: Get everything in one archive
- **Includes**:
  - All uploaded/processed files
  - metadata.json (structured data)
  - captions.txt (readable captions file)
- **Ready for Schedulers**: Perfect for bulk uploads
- **Timestamped**: Each ZIP has unique timestamp

#### 📤 Scheduler Export
- **Multiple Formats**: CSV or JSON
- **Scheduler Support**:
  - Buffer
  - Publer
  - Later
  - Meta Business Suite
- **Complete Metadata**: Captions, hashtags, file references

---

## 🔄 Complete Workflow

### 1. Upload
```
Choose Media Type → Upload Files → Auto-Generate Captions
```
- Files saved to organized folders
- Captions and hashtags created instantly
- Session tracks all files

### 2. Edit
```
Select File → Edit Caption → Manage Hashtags → Apply Edits
```
- Each file editable individually
- Audio trimming with FFmpeg
- Image cropping with Pillow
- Changes saved to session

### 3. Preview
```
Review Content → Test Playback → Verify Captions
```
- Audio player for testing
- Image preview for visual check
- Caption and hashtag review

### 4. Export
```
Download ZIP → or → Download Individual → or → Export Metadata
```
- ZIP: Everything in one file
- Individual: Specific files with edits
- Metadata: For scheduler imports

---

## 🛠️ Technical Features

### Backend (Flask)
- **Session Management**: Static secret key for persistence
- **File Organization**: Separate folders for audio/images
- **Auto-Generation API**: Caption and hashtag endpoints
- **Processing API**: Audio trim and image crop
- **Export API**: ZIP, CSV, JSON formats
- **Update API**: Save caption/hashtag changes

### Frontend (Vanilla JS)
- **No Framework Dependencies**: Pure JavaScript
- **Dynamic UI**: Real-time updates
- **Session Loading**: Fetch files on page load
- **Fetch API**: Modern async requests
- **Form Validation**: Client-side checks

### File Storage
```
uploads/
├── audio/          # MP3, WAV, M4A, AAC
├── images/         # JPG, PNG, WEBP
output/             # Processed files
scheduler_export/   # CSV, JSON exports
```

### Session Data Structure
```json
{
  "uploaded_files": [
    {
      "filename": "track.mp3",
      "original_name": "track.mp3",
      "type": "audio",
      "path": "audio/track.mp3",
      "caption": "Auto-generated caption here",
      "hashtags": ["#music", "#audio", "#content"],
      "edits": {
        "start_time": 0,
        "duration": 15
      }
    }
  ]
}
```

---

## 📋 API Endpoints

### Upload & Session
- `POST /api/upload` - Upload file with auto-generation
- `GET /api/session/files` - Get all uploaded files
- `POST /api/session/clear` - Clear session

### Editing & Processing
- `POST /api/file/update` - Update caption/hashtags/edits
- `POST /api/process` - Process audio/image with edits
- `POST /api/generate-content` - Regenerate caption/hashtags

### Export & Download
- `POST /api/export` - Export metadata (CSV/JSON)
- `POST /api/export-zip` - Export everything as ZIP
- `GET /download/<filename>` - Download individual file
- `GET /api/preview/<filename>` - Preview file

---

## 🎨 UI Features

### Responsive Design
- Desktop: 3-column editor layout
- Tablet: 2-column stacked layout
- Mobile: Single column, full-width

### Visual Feedback
- Upload progress indicator
- Character counter
- File type icons (🎵 🖼️)
- Active file highlighting
- Hashtag badges with gradients

### User Experience
- Empty states with helpful prompts
- Confirmation dialogs for destructive actions
- Success/error alerts
- Smooth transitions and hover effects

---

## 🚀 Quick Start

### 1. Upload Files
```bash
# Start the app
python app.py

# Visit http://localhost:5000
# Click "Upload Files"
# Choose Audio or Image
# Drag and drop files
```

### 2. Edit Content
```bash
# Go to Editor
# Click a file to select
# Edit caption and hashtags
# Apply audio trim or image crop
# Save changes
```

### 3. Export
```bash
# Go to Preview
# Click "Download ZIP" for everything
# Or download files individually
# Or export metadata for schedulers
```

---

## 💡 Pro Tips

### Caption Writing
- Keep it short for TikTok (150 chars)
- Use emojis strategically
- Front-load important info
- Use character counter to stay within limits

### Hashtag Strategy
- Mix popular and niche tags
- Use 5-10 hashtags per post
- Click regenerate for fresh ideas
- Remove irrelevant tags

### Audio Editing
- 15 seconds perfect for Reels/TikTok
- Start at the best part (hook)
- Use decimal precision for exact timing
- Preview before processing

### Image Cropping
- 1:1 for Instagram feed posts
- 9:16 for Stories and Reels
- 4:5 for better mobile visibility
- 16:9 for YouTube thumbnails

### Batch Workflow
- Upload all files at once
- Edit captions systematically
- Use ZIP export for scheduler bulk upload
- Keep metadata.json for reference

---

## 🔧 Customization

### Adding More Platforms
Edit `config/config.yaml`:
```yaml
platforms:
  your_platform:
    display_name: "Your Platform"
    video:
      min_duration: 10
      max_duration: 60
```

### Custom Caption Templates
Edit `social_studio/caption_generator.py`:
```python
def _generate_template_caption(self, content_type, platform, filename):
    # Add your templates here
    templates = {
        'your_platform': [
            "Your custom template 1",
            "Your custom template 2"
        ]
    }
```

### Custom Hashtag Sets
Edit `config/config.yaml`:
```yaml
hashtag_sets:
  your_category:
    - "#tag1"
    - "#tag2"
```

---

## 📦 Dependencies

### Core
- Flask 2.3.0
- Werkzeug 2.3.0
- PyYAML 6.0
- python-dateutil 2.8.0

### Processing
- Pillow 10.0.0 (image processing)
- FFmpeg (audio processing - external)

### No Video Dependencies
- ❌ moviepy (removed)
- ❌ opencv (removed)
- ❌ pydub (removed)
- ❌ numpy (removed)

---

## 🐛 Troubleshooting

### Files Not Uploading
- Check file extensions (must be supported format)
- Ensure uploads/audio/ and uploads/images/ folders exist
- Check browser console for errors

### Captions Not Generating
- Verify caption_generator.py is working
- Check config.yaml has caption templates
- Try manual caption entry

### Audio Trim Not Working
- Install FFmpeg: `winget install FFmpeg`
- Verify FFmpeg in PATH
- Check audio file is valid format

### ZIP Export Empty
- Ensure files are uploaded
- Check session has uploaded_files
- Verify file paths are correct

### Session Lost After Restart
- Verify secret key is static (not random)
- Check app.py has: `app.secret_key = 'social-studio-secret-key-2026'`
- Don't clear browser cookies

---

## 🎓 Architecture

### Flow Diagram
```
┌─────────────┐
│   Upload    │ → Auto-generate captions/hashtags
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Session   │ → Store files + metadata
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Editor    │ → Edit captions, trim, crop
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Preview   │ → Test playback, review
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Export    │ → ZIP / Individual / Metadata
└─────────────┘
```

### Module Responsibilities
- **app.py**: Routes, session, file handling
- **content_processor.py**: Audio trim, image crop
- **caption_generator.py**: Caption and hashtag generation
- **export_manager.py**: CSV/JSON export
- **config_manager.py**: Configuration loading

---

## 📄 License

MIT License - Free for personal and commercial use

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📞 Support

- **GitHub Issues**: Report bugs or request features
- **Documentation**: README.md and SETUP.md
- **Email**: Contact through GitHub profile

---

**Built with ❤️ for content creators**

*Social Studio - Your complete social media content workflow*
