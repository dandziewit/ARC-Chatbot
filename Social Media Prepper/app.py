"""
Audio Clip Maker & Format Converter
Simple Flask app for converting and clipping audio files
"""

from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
import tempfile
from datetime import datetime
import logging
import subprocess

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'audio-converter-2026'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = Path('uploads')
app.config['OUTPUT_FOLDER'] = Path('output')

# Create required directories with subdirectories
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
(app.config['UPLOAD_FOLDER'] / 'audio').mkdir(exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)

# Allowed file extensions
AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'opus'}
ALLOWED_FORMATS = {'mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg'}

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    """Upload page"""
    return render_template('upload.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload audio file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if '.' not in file.filename:
        return jsonify({'success': False, 'error': 'File has no extension'}), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    
    if ext not in AUDIO_EXTENSIONS:
        return jsonify({'success': False, 'error': f'Unsupported format: {ext}. Supported: MP3, WAV, M4A, AAC, FLAC, OGG'}), 400
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        
        upload_path = app.config['UPLOAD_FOLDER'] / 'audio' / safe_filename
        file.save(str(upload_path))
        
        # Initialize session
        if 'uploaded_files' not in session:
            session['uploaded_files'] = []
        
        file_info = {
            'filename': safe_filename,
            'original_name': filename,
            'path': str(upload_path),
            'format': ext
        }
        
        session['uploaded_files'].append(file_info)
        session.modified = True
        
        return jsonify({
            'success': True,
            'filename': safe_filename,
            'original_name': filename,
            'format': ext
        })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/editor')
def editor():
    """Editor page"""
    uploaded_files = session.get('uploaded_files', [])
    return render_template('editor.html', files=uploaded_files)

@app.route('/api/session/files', methods=['GET'])
def get_session_files():
    """Get uploaded files from session"""
    return jsonify({
        'files': session.get('uploaded_files', [])
    })

@app.route('/api/convert', methods=['POST'])
def convert_audio():
    """Convert audio to different format and optionally trim"""
    data = request.json
    filename = data.get('filename')
    output_format = data.get('output_format', 'mp3').lower()
    start_time = float(data.get('start_time', 0))
    duration = float(data.get('duration', 0))
    
    if not filename or output_format not in ALLOWED_FORMATS:
        return jsonify({'error': 'Invalid format or filename'}), 400
    
    try:
        uploaded_files = session.get('uploaded_files', [])
        file_info = None
        for f in uploaded_files:
            if f['filename'] == filename:
                file_info = f
                break
        
        if not file_info:
            return jsonify({'error': 'File not found'}), 404
        
        input_path = file_info['path']
        
        # Create output filename
        base_name = file_info['original_name'].rsplit('.', 1)[0]
        output_filename = f"{base_name}_converted.{output_format}"
        output_path = app.config['OUTPUT_FOLDER'] / output_filename
        
        # Build FFmpeg command
        cmd = ['ffmpeg', '-i', input_path]
        
        # Add trimming if specified
        if start_time > 0 or duration > 0:
            cmd.extend(['-ss', str(start_time)])
            if duration > 0:
                cmd.extend(['-t', str(duration)])
        
        # Add output format options
        if output_format == 'mp3':
            cmd.extend(['-q:a', '2'])  # Good quality
        elif output_format == 'wav':
            cmd.extend(['-acodec', 'pcm_s16le'])
        elif output_format == 'aac':
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
        elif output_format == 'ogg':
            cmd.extend(['-c:a', 'libvorbis', '-q:a', '5'])
        
        cmd.extend(['-y', str(output_path)])
        
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return jsonify({'error': 'Conversion failed. Check FFmpeg installation.'}), 500
        
        return jsonify({
            'success': True,
            'filename': output_filename,
            'format': output_format,
            'download_url': f'/download/{output_filename}'
        })
    
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download converted file"""
    try:
        file_path = app.config['OUTPUT_FOLDER'] / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/clear', methods=['POST'])
def clear_session():
    """Clear all uploaded files"""
    session.clear()
    return jsonify({'success': True})

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large (max 100MB)'}), 413

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server error"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5000)
