# FufuRemind Discord Bot - Usage Guide

## 🚀 Quick Start

### 1. Setup Discord Bot
1. Go to https://discord.com/developers/applications
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token
5. Update `config/.env` with your token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```

### 2. Invite Bot to Server
1. In Discord Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Send Messages
   - Use Slash Commands
   - Add Reactions
   - Kick Members (for validation enforcement)
   - Manage Messages
4. Copy and visit the generated URL to invite the bot

### 3. Start the Bot
```bash
# Activate virtual environment
source venv/bin/activate

# Start the bot
python main.py
```

## 📋 Commands

### `/reminder_add`
Create a new reminder (admin only)
- **user**: Discord user to remind
- **frequency**: `hourly`, `daily`, `weekly`, or `monthly`
- **message**: The reminder message
- **validation_required**: Whether user must react with ✅ (optional)

**Example:**
```
/reminder_add user:@john frequency:daily message:"Daily standup at 9 AM" validation_required:True
```

### `/reminder_list`
List your reminders (or another user's if admin)
- **user**: User to list reminders for (optional, admin only)

### `/reminder_delete`
Delete a reminder by ID
- **reminder_id**: ID of the reminder to delete

### `/reminder_pause`
Pause a reminder temporarily
- **reminder_id**: ID of the reminder to pause

### `/reminder_resume`
Resume a paused reminder
- **reminder_id**: ID of the reminder to resume

### `/reminder_stats`
Show system-wide reminder statistics

## 🔐 Permissions

### Admin Users
Users with "Manage Server" permission can:
- Create reminders for any user
- View anyone's reminders
- Delete/pause/resume any reminder
- View system statistics

### Regular Users
- Can only view their own reminders
- Cannot create new reminders
- Can only delete/pause/resume their own reminders

## ✅ Validation System

When `validation_required` is enabled for a reminder:

1. **Reminder Sent**: Bot sends the reminder message
2. **Reaction Added**: Bot automatically adds ✅ reaction
3. **User Response**: User must click ✅ within 48 hours
4. **Automatic Enforcement**: Users who don't validate are kicked from server

### Validation Flow
```
Reminder Sent → ✅ Added → User Clicks ✅ → Validation Complete
                      ↓
                 48h Timeout → User Kicked
```

## 🔧 Configuration

### Environment Variables (`config/.env`)
```bash
# Required
DISCORD_TOKEN=your_bot_token

# Optional
VALIDATION_TIMEOUT_HOURS=48
COMMAND_PREFIX=!
LOG_LEVEL=INFO
DATABASE_URL=sqlite+aiosqlite:///data/reminders.db
```

### JSON Config (`config/config.json`)
```json
{
    "command_prefix": "!",
    "log_level": "INFO"
}
```

## 📊 Features

### ✅ Completed Features
- **Slash Commands**: Modern Discord command interface
- **Admin Controls**: Permission-based reminder management
- **User Validation**: Automated reaction-based validation
- **Flexible Scheduling**: Hourly to monthly frequencies
- **Guild Management**: Automatic cleanup on bot removal
- **Statistics**: System-wide usage monitoring
- **Error Handling**: Graceful error recovery
- **Logging**: Comprehensive operation logging

### 🎯 Core Functionality
1. **Admin creates reminder** via `/reminder_add`
2. **Bot schedules execution** using background tasks
3. **Message sent automatically** at specified intervals
4. **Optional validation** via ✅ reaction (48h timeout)
5. **User management** with automatic enforcement

## 🐛 Troubleshooting

### Bot Won't Start
1. Check Discord token is valid in `config/.env`
2. Ensure bot has correct permissions in Discord
3. Verify database directory exists: `mkdir -p data logs`

### Commands Not Working
1. Ensure bot has "Use Slash Commands" permission
2. Try inviting bot again with correct scopes
3. Check bot is online in Discord

### Validation Not Working
1. Verify bot has "Add Reactions" and "Kick Members" permissions
2. Check bot role is higher than users it needs to kick
3. Ensure validation timeout is properly configured

### Database Issues
1. Check `data/` directory exists and is writable
2. Verify DATABASE_URL in config uses `sqlite+aiosqlite://`

## 📝 Logs

Logs are stored in `logs/fufu_remind.log` and include:
- Bot startup/shutdown events
- Command executions
- Validation events
- Error messages
- Performance metrics

## 🔒 Security Notes

- Only admins can create reminders
- User input is validated and sanitized
- No sensitive data logged
- Graceful handling of Discord API failures
- Safe user management with proper permission checks

## 🎉 Success!

Your FufuRemind bot is now ready for production use! The enterprise-grade architecture ensures reliability, maintainability, and scalability for any Discord server size.