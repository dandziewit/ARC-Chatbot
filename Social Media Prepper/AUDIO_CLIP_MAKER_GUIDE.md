# Audio Clip Maker - Quick Start Guide

## What is This?
Audio Clip Maker is a simple web tool that lets you:
- **Trim audio** - Cut audio to specific start time and duration
- **Convert formats** - Change between MP3, WAV, M4A, AAC, OGG, FLAC
- **Download** - Get your processed audio instantly

## Supported Audio Formats
**Upload:** MP3, WAV, M4A, AAC, FLAC, OGG, WMA, OPUS
**Convert to:** MP3, WAV, M4A, AAC, OGG, FLAC

## How to Use

### 1. Upload Your Audio
1. Go to http://localhost:5000
2. Click "Get Started"
3. Drag & drop audio file OR click to browse
4. File appears in the list

### 2. Edit in Editor
1. Click "Continue to Editor"
2. Select audio file from dropdown
3. Audio preview loads with player controls

### 3. Trim (Optional)
1. Enter **Start Time** in seconds (e.g., 5 for 5 seconds)
2. Enter **Duration** in seconds (e.g., 30 for 30 seconds)
3. Leave Duration as 0 to use entire audio

### 4. Select Format
1. Click format button: MP3, WAV, M4A, AAC, OGG, or FLAC
2. Selected format appears highlighted

### 5. Convert & Download
1. Click "Convert & Download"
2. Processing happens (~5-15 seconds depending on file size)
3. File downloads automatically to your Downloads folder

## File Naming
- Downloaded files are named: `{original_name}_converted.{format}`
- Example: `song_converted.wav`

## Tips
- **No audio length limit** - Works with files of any duration
- **Quick preview** - Play audio before converting
- **Keep original** - Uploaded files remain unchanged
- **Batch processing** - Upload multiple files, convert one at a time
- **No metadata** - Simple conversion, no audio tags modified

## Technical Details
- Storage: Files stored in `uploads/audio/` during session
- Converted files saved to: `output/`
- Downloads available for 24 hours
- Uses FFmpeg for conversion (must be installed on system)

## Keyboard Shortcuts
- No keyboard shortcuts currently

## What Was Removed
❌ Caption generation
❌ Hashtag generation
❌ Image support
❌ Scheduler export
❌ Social media optimization

## Support
If conversion fails:
1. Check that FFmpeg is installed on your system
2. Verify audio file is not corrupted
3. Try a different audio format
4. Check file isn't extremely large (>100MB)

---

**Version:** Audio Clip Maker v1.0 (Simplified)
**Last Updated:** January 2026
