# Tools

Tools for development and debug.

# Note

## Quick Video Stream Preview

```bash
ffplay -fflags nobuffer -flags low_delay -framedrop -f h264 tcp://robomaster:40921
```

## Record Video Stream

```bash
ffmpeg -i tcp://robomaster:40921 record.mp4
```