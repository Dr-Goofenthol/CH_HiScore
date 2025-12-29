# Requested Features & Known Issues
**Source:** Direct user requests and discussions
**Last Updated:** 2025-12-27

---

## 🎯 Features Requested by User

**Note:** Based on current session and available conversation history, I don't have record of specific feature requests that were shelved. If you have features you'd like to track, please let me know and I'll add them here.

### From Conversation History
- No pending feature requests currently documented

---

## 🐛 Known Bugs & Issues to Fix

### Currently Identified Issues

**None critical.** All known issues from v2.4.15 development have been resolved:
- ✅ resolvehashes command (was broken, now fixed)
- ✅ Charter data pipeline (was incomplete, now operational)
- ✅ Settings.ini parsing (was manual/broken, now uses configparser)
- ✅ Missing parse_song_ini import (was causing silent failures, now imported)

### Potential Minor Issues

Based on codebase review, these might exist but haven't been confirmed:

1. **OCR Accuracy** - Windows OCR sometimes misreads results screen
   - Not confirmed as actively problematic
   - May need testing to validate if issue exists

2. **Large Song Library Performance** - resolvehashes might be slow with 10,000+ songs
   - Not confirmed, theoretical issue
   - Current testing: 3,188 songs scanned in <30 seconds (acceptable)

3. **Unicode Console Output** - Some special characters in song titles might display incorrectly
   - Partially addressed (changed ✓ to + in some places)
   - May still have issues in other areas

---

## 📝 Notes

**Important:** This list is intentionally sparse because I don't have access to:
- Earlier conversation sessions where features may have been discussed
- Feature requests you may have made in previous development cycles
- Issues you've observed but haven't mentioned in current session

**To populate this list, please let me know:**
1. Any features you've previously asked for that were shelved
2. Any bugs or issues you're aware of that need fixing
3. Any improvements you'd like to prioritize

This will give us an accurate working list based on your actual needs rather than speculation.
