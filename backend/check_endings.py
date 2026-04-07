import sqlite3

conn = sqlite3.connect('data/novels.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('select id, title, updated_at from novels order by updated_at desc limit 3')
novels = [dict(r) for r in cur.fetchall()]
for n in novels:
    print('=== ' + n['title'] + ' (' + n['id'] + ') ===')
    cur.execute('select chapter_num, title, word_count, content from chapters where novel_id=? order by chapter_num', (n['id'],))
    for ch in cur.fetchall():
        content = ch['content'] or ''
        tail = content[-200:]
        print('  Ch' + str(ch['chapter_num']) + ' (' + str(ch['word_count']) + ' chars) tail: ...' + tail)
    print()
conn.close()
