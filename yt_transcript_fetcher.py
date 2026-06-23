from youtube_transcript_api import YouTubeTranscriptApi
import re, os, sys, time
from core.env_config import get_wiki_research_dir

def get_video_id(url):
    m = re.search(r'[?&]v=([^&]+)', url)
    return m.group(1) if m else url

def fetch_transcript(url, index=None, out_dir=None):
    if out_dir is None:
        out_dir = get_wiki_research_dir()
    vid = get_video_id(url)
    api = YouTubeTranscriptApi()
    langs = ('zh-Hans','zh-Hant','en')
    last_err = None
    for attempt in range(5):
        try:
            transcript = api.fetch(vid, languages=langs)
            lines = [f'[{s.start:.2f}] {s.text}' for s in transcript]
            text = '\n'.join(lines)
            idx = f'-{index}' if index else ''
            path = os.path.join(out_dir, f'2026-06-23-youtube-trading-sop{idx}-transcript.txt')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'saved {path}\nsize {len(text)}')
            return path
        except Exception as e:
            last_err = e
            print(f'Attempt {attempt+1} error: {type(e).__name__} {e}')
            time.sleep(2 ** attempt)
    raise last_err

if __name__ == '__main__':
    fetch_transcript(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
