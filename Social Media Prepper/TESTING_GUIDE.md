# 🧪 Quick Test Guide

## Test the Complete Workflow

### ✅ Test 1: Upload with Auto-Generation
1. Go to http://localhost:5000
2. Click "Upload Files"
3. Select "Audio" or "Image"
4. Upload a test file
5. **Expected**: Caption auto-generates and appears below file name
6. **Verify**: File appears in list with caption preview

### ✅ Test 2: Editor - Captions & Hashtags
1. Click "Continue to Editor"
2. Click on a file in the left panel
3. **Verify**: 
   - Auto-generated caption appears in textarea
   - Hashtags display as colored badges
   - Character counter shows caption length
4. Edit the caption
5. Click hashtag badge to remove it
6. Type new hashtag and click "Add"
7. Click "Save Changes"
8. **Expected**: "✅ Changes saved!" alert

### ✅ Test 3: Audio Editing
1. Select an audio file
2. Set start time (e.g., 5 seconds)
3. Set duration (e.g., 15 seconds)
4. Click "Apply Trim"
5. **Expected**: "✅ Audio trimmed successfully!" alert
6. **Note**: Requires FFmpeg installed

### ✅ Test 4: Image Editing
1. Select an image file
2. Choose aspect ratio (e.g., 9:16 for Story)
3. Click "Apply Crop"
4. **Expected**: "✅ Image cropped successfully!" alert

### ✅ Test 5: ZIP Export
1. Click "Preview & Export"
2. Scroll to "Download Everything" section
3. Click "📥 Download ZIP"
4. **Expected**: 
   - ZIP file downloads
   - Contains all files
   - Includes metadata.json
   - Includes captions.txt

### ✅ Test 6: Individual Download
1. In Preview page
2. Click "⬇ Download" button on any file
3. **Expected**: File downloads with edits applied

### ✅ Test 7: Scheduler Export
1. In Preview page
2. Select scheduler (e.g., Buffer)
3. Select format (CSV or JSON)
4. Click "📤 Export Metadata"
5. **Expected**: Export file downloads

### ✅ Test 8: Session Persistence
1. Upload some files
2. Close browser
3. Reopen http://localhost:5000/editor
4. **Expected**: Files still appear
5. **Verify**: Secret key is static (not random)

### ✅ Test 9: Clear Session
1. In Editor page
2. Click "🗑️ Clear All"
3. Confirm dialog
4. **Expected**: Redirect to upload page
5. **Verify**: All files cleared

### ✅ Test 10: Multiple Files
1. Upload 3-5 files at once
2. Navigate to Editor
3. Click through each file
4. Edit captions for each
5. Save all changes
6. Go to Preview
7. **Verify**: All files show with captions
8. Download ZIP
9. **Verify**: ZIP contains all files + metadata

---

## 🐛 Common Issues & Solutions

### Issue: Caption not auto-generating
**Solution**: Check `caption_generator.py` - template fallback should work

### Issue: Hashtags not appearing
**Solution**: Verify `config.yaml` has hashtag_sets

### Issue: Audio trim fails
**Solution**: Install FFmpeg - `winget install FFmpeg`

### Issue: Image crop fails
**Solution**: Verify Pillow installed - `pip install pillow`

### Issue: ZIP export empty
**Solution**: Check session has files - visit `/api/session/files`

### Issue: Files disappear after restart
**Solution**: Verify `app.secret_key = 'social-studio-secret-key-2026'` (static)

---

## 📊 Test Checklist

- [ ] Upload audio file → caption auto-generates
- [ ] Upload image file → caption auto-generates
- [ ] Edit caption → save works
- [ ] Add hashtag → appears as badge
- [ ] Remove hashtag → badge disappears
- [ ] Regenerate hashtags → new hashtags appear
- [ ] Trim audio → FFmpeg processes file
- [ ] Crop image → Pillow processes file
- [ ] Preview audio → player works
- [ ] Preview image → image displays
- [ ] Download individual file → file downloads
- [ ] Download ZIP → contains files + metadata
- [ ] Export CSV → scheduler file downloads
- [ ] Session persists → files survive browser close
- [ ] Clear all → session empties

---

## 🎯 Success Criteria

✅ **Upload**: Files upload with auto-generated captions
✅ **Editor**: Captions/hashtags editable per file
✅ **Processing**: Audio trim and image crop work
✅ **Preview**: Files display correctly
✅ **Export**: ZIP contains all files + metadata
✅ **Session**: Data persists across reloads
✅ **UI**: Responsive and intuitive
✅ **Errors**: Handled gracefully with alerts

---

## 🚀 Production Readiness

### Before Deploying:
1. Change `debug=True` to `debug=False` in app.py
2. Use production WSGI server (Gunicorn/uWSGI)
3. Set environment variable for secret key
4. Configure reverse proxy (Nginx/Apache)
5. Enable HTTPS
6. Set up file storage limits
7. Add rate limiting
8. Implement user authentication (if needed)

---

**All tests should pass before sharing with friends!**
