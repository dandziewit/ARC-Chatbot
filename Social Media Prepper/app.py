"""
Social Studio - Web Application
Flask-based browser interface for social media content preparation
"""

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
import tempfile
from datetime import datetime
import secrets

from social_studio.config_manager import ConfigManager
from social_studio.content_processor import ContentProcessor
from social_studio.caption_generator import CaptionGenerator
from social_studio.export_manager import ExportManager

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = Path('uploads')
app.config['OUTPUT_FOLDER'] = Path('output')
app.config['SESSION_TYPE'] = 'filesystem'

# Create required directories
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)

# Initialize Social Studio components
config_file = Path(__file__).parent / 'config' / 'config.yaml'
config_manager = ConfigManager(str(config_file))
content_processor = ContentProcessor(config_manager)
caption_generator = CaptionGenerator(config_manager)
export_manager = ExportManager(config_manager)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'audio': {'mp3', 'wav', 'm4a', 'aac'},
    'video': {'mp4', 'mov', 'avi', 'mkv'},
    'image': {'jpg', 'jpeg', 'png', 'webp'}
}

def allowed_file(filename, file_type):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())

def get_file_type(filename):
    """Determine file type from extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return None

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    """Upload page"""
    return render_template('upload.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Determine file type
    file_type = get_file_type(file.filename)
    if not file_type:
        return jsonify({'error': 'Unsupported file type'}), 400
    
    if not allowed_file(file.filename, file_type):
        return jsonify({'error': f'Invalid {file_type} file'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_filename = f"{timestamp}_{filename}"
    filepath = app.config['UPLOAD_FOLDER'] / safe_filename
    file.save(filepath)
    
    # Store in session
    if 'uploaded_files' not in session:
        session['uploaded_files'] = []
    
    session['uploaded_files'].append({
        'filename': safe_filename,
        'original_name': filename,
        'type': file_type,
        'path': str(filepath)
    })
    session.modified = True
    
    return jsonify({
        'success': True,
        'filename': safe_filename,
        'type': file_type
    })

@app.route('/editor')
def editor():
    """Media editor page"""
    uploaded_files = session.get('uploaded_files', [])
    return render_template('editor.html', files=uploaded_files)

@app.route('/api/process', methods=['POST'])
def process_media():
    """Process media (trim, crop, etc.)"""
    data = request.json
    file_info = data.get('file')
    media_type = file_info.get('type')
    
    try:
        if media_type == 'audio':
            # Trim audio
            start_time = data.get('start_time', 0)
            duration = data.get('duration', 15)
            input_path = Path(file_info['path'])
            output_dir = app.config['OUTPUT_FOLDER']
            
            output_path = content_processor.clip_audio(
                input_path,
                output_dir,
                start_time,
                duration
            )
            
            return jsonify({
                'success': True,
                'output_path': str(output_path),
                'filename': output_path.name
            })
        
        elif media_type == 'image':
            # Process image
            input_path = Path(file_info['path'])
            aspect_ratio = data.get('aspect_ratio', '1:1')
            
            # Basic image processing (you can expand this)
            output_path = app.config['OUTPUT_FOLDER'] / input_path.name
            
            return jsonify({
                'success': True,
                'output_path': str(output_path),
                'filename': output_path.name
            })
        
        else:
            return jsonify({'error': 'Unsupported media type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    """Generate captions and hashtags"""
    data = request.json
    platform = data.get('platform', 'instagram')
    media_type = data.get('media_type', 'image')
    
    try:
        # Generate caption
        caption = caption_generator.generate_caption(platform)
        
        # Generate hashtags
        hashtags = caption_generator.generate_hashtags(media_type, platform)
        
        return jsonify({
            'success': True,
            'caption': caption,
            'hashtags': hashtags
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview')
def preview():
    """Preview page for generated content"""
    uploaded_files = session.get('uploaded_files', [])
    processed_files = session.get('processed_files', [])
    
    return render_template('preview.html', 
                         uploaded_files=uploaded_files,
                         processed_files=processed_files)

@app.route('/api/export', methods=['POST'])
def export_content():
    """Export content for schedulers"""
    data = request.json
    posts = data.get('posts', [])
    scheduler = data.get('scheduler', 'buffer')
    format_type = data.get('format', 'csv')
    
    try:
        if format_type == 'csv':
            output_file = export_manager.export_to_csv(posts, scheduler)
        else:
            output_file = export_manager.export_to_json(posts, scheduler)
        
        return jsonify({
            'success': True,
            'file': str(output_file),
            'filename': output_file.name
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download processed file"""
    try:
        # Check in output folder
        file_path = app.config['OUTPUT_FOLDER'] / filename
        if file_path.exists():
            return send_file(file_path, as_attachment=True)
        
        # Check in scheduler export folder
        export_path = Path('scheduler_export') / filename
        if export_path.exists():
            return send_file(export_path, as_attachment=True)
        
        return jsonify({'error': 'File not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/platforms')
def get_platforms():
    """Get available platforms"""
    platforms = config_manager.config.get('platforms', {})
    return jsonify({
        'platforms': [
            {'id': name, 'name': name.capitalize(), 'enabled': info.get('enabled', True)}
            for name, info in platforms.items()
            if info.get('enabled', True)
        ]
    })

@app.route('/api/session/clear', methods=['POST'])
def clear_session():
    """Clear session data"""
    session.clear()
    return jsonify({'success': True})

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large (max 50MB)'}), 413

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server error"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5000)
