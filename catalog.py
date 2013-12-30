import os
import operator
import sqlite3
import sys
import itertools

from mutagen.mp3 import MP3

db_full_path = 'C:\\Users\\kevin\\Music\\music.sqlite'
music_full_path = 'C:\\Users\\kevin\\Music\\Amazon MP3\\'

def install():
    con = sqlite3.connect(db_full_path)
    con.execute('create table music(id integer primary key autoincrement, artist text, album text, track text, title text, fullpath text)')
    con.commit()
    con.close()

def rebuild():
    con = sqlite3.connect(db_full_path)
    songs = list(list_music(music_full_path))
    con.execute('delete from music')
    con.executemany('insert into music(artist, album, track, title, fullpath) values (?, ?, ?, ?, ?)', songs)
    con.commit()
    con.close()

def search(query):
    if not os.path.exists(db_full_path):
        install()
        rebuild()
    con = sqlite3.connect(db_full_path)
    search_term = SearchTerm(query)
    sql = SearchTermSql(search_term)
    sql = unicode(sql)
    for id, artist, album, track, title, fullpath in con.execute(sql):
        name = fullpath.replace(music_full_path, '')
        name = name.replace('.mp3', '')
        yield dict(id=id, artist=artist, album=album, track=track, title=title, name=name)
    con.close()

def get_by_id(id):
    if not os.path.exists(db_full_path):
        install()
        rebuild()
    con = sqlite3.connect(db_full_path)
    cur = con.cursor()
    sql = 'select id, artist, album, track, title, fullpath from music where id=?'
    cur.execute(sql, (id,))
    row = cur.fetchone()
    con.close()
    return row

def group_results(songs):
    """Return songs grouped by artist and album. By convention, all song files should
    use the following folder naming convention: {artist}/{album}/{title}.mp3"""
    byartist = lambda song: song['artist']
    byalbum = lambda song: song['album']
    result = [
        dict(name=artist_name, albums=[
            dict(name=album_name, songs=list(album_songs))
            for album_name, album_songs in itertools.groupby(artist_songs, byalbum)])
        for artist_name, artist_songs in itertools.groupby(songs, byartist)]
    return result

def list_music(path):
    ID3_23 = (2, 3, 0)
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            if file.endswith(('.mp3')):
                fullpath = unicode(os.path.join(dirpath, file), errors='ignore')
                mp3file = MP3(fullpath)
                version = mp3file.tags.version
                if version == ID3_23:
                    artist = unicode(mp3file.tags['TPE1'])
                    album = unicode(mp3file.tags['TALB'])
                    track = unicode(mp3file.tags['TRCK'])
                    title = unicode(mp3file.tags['TIT2'])
                else:
                    raise Exception('ID3 version ' + str(version) + ' not supported')
                yield artist, album, track, title, fullpath


class SearchTerm(object):
    """
    term          := .[^" ]+
    exact_term    := "term+"
    positive_term := term | exact_term
    negative_term := -(positive_term | negative_term)
    terms         := (positiveterm | negative_term)+

    Examples:
    "the beatles" "flaming lips" nirvana -"animal collective" -houston
    "the beatles" -collective
    """

    def __init__(self, input):
        self.input = input
        self.position = 0

    def __iter__(self):
        while True:
            token = self.next_token()
            if token:
                yield token
            else:
                break
        raise StopIteration

    def done(self):
        return self.position >= len(self.input)

    def current(self):
        if self.done():
            return False
        return self.input[self.position]

    def next(self, expected=None):
        if expected and self.done():
            raise Exception('Expected "%s" but parsing ended' % (expected))
        if self.done():
            return False
        char = self.input[self.position]
        if expected and char != expected:
            raise Exception('Expected "%s" but received "%s"' % (expected, char))
        self.position += 1
        return char

    def next_token(self):
        return self.negative_term() or self.positive_term()

    def negative_term(self):
        if self.current() == '-':
            self.next('-')
            return ('NEGATIVE', self.positive_term())
        return False

    def positive_term(self):
        term = self.exact_term() or self.term()
        if term:
            return ('POSITIVE', term)
        return False

    def exact_term(self):
        quote_char = self.current()
        if self.current() in ('"', "'"):
            self.next(quote_char)
            terms = []
            while True:
                term = self.term(blacklist=(quote_char,))
                if not term:
                    break
                terms.append(term)
            self.next(quote_char)
            self.whitespace()
            return ('EXACT', terms)
        return False

    def term(self, blacklist=('"', "'")):
        result = []
        while True:
            if self.current() == ' ' or self.current() in blacklist:
                break
            char = self.next_char()
            if not char:
                break
            result.append(char)
        if len(result) == 0:
            return False
        self.whitespace()
        result = ''.join(result)
        return ('TERM', result)

    def next_char(self):
        return self.escaped_char() or self.next()

    def escaped_char(self):
        if self.current() == '\\':
            self.next('\\')
            return self.next()
        return False

    def whitespace(self):
        while self.current() == ' ':
            self.next(' ')


class SearchTermSql(object):

    def __init__(self, search_term):
        self.terms = list(search_term)

    def __str__(self):
        return 'SELECT id, artist, album, track, title, fullpath FROM music' + self.where_clause()

    def where_clause(self):
        positive_terms = [(type, value) for (type, value) in self.terms if type == 'POSITIVE']
        positive_terms = [self.term_where_clause(term) for term in positive_terms]
        negative_terms = [(type, value) for (type, value) in self.terms if type == 'NEGATIVE']
        negative_terms = [self.term_where_clause(term) for term in negative_terms]
        result = []
        if len(positive_terms) > 0:
            result.append('(' + ' OR '.join(positive_terms) + ')')
        if len(negative_terms) > 0:
            result.append('NOT (' + ' OR '.join(negative_terms) + ')')
        result = ' AND '.join(result)
        if len(result) == 0:
            return ''
        return ' WHERE ' + result

    def term_where_clause(self, term):
        type, value = term
        if type == 'TERM':
            escaped_value = value.replace("'", "''")
            cols = ['artist', 'album', 'title', 'fullpath']
            return '(' + ' OR '.join([u"{0} LIKE '%{1}%'".format(col, escaped_value) for col in cols]) + ')'
        elif type == 'EXACT':
            return '(' + ' AND '.join([self.term_where_clause(t) for t in value]) + ')'
        elif type in ('POSITIVE', 'NEGATIVE'):
            return self.term_where_clause(value)


if __name__ == '__main__':
    query = "\"Christopher O'Riley\" "#' '.join(sys.argv[1:])
    results = search(query)
    print list(results)

