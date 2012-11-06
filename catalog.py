import os
import sqlite3
import sys
import itertools

db_full_path = '/cygdrive/f/music.db'
music_full_path = '/cygdrive/f/Vuze Downloads/'

def install():
    con = sqlite3.connect(db_full_path)
    con.execute('create table music(id integer primary key autoincrement, fullpath text)')
    con.commit()
    con.close()

def rebuild():
    con = sqlite3.connect(db_full_path)
    songs = list(list_music(music_full_path))
    con.execute('delete from music')
    con.executemany('insert into music(fullpath) values (?)', songs)
    con.commit()
    con.close()

def search(query):
    if not os.path.exists(db_full_path):
        install()
        rebuild()
    con = sqlite3.connect(db_full_path)
    search_term = SearchTerm(query)
    sql = SearchTermSql(search_term)
    sql = str(sql)
    for id, fullpath in con.execute(sql):
        path = fullpath.replace(music_full_path, '')
        yield dict(id=id, name=path)
    con.close()

def get_by_id(id):
    if not os.path.exists(db_full_path):
        install()
        rebuild()
    con = sqlite3.connect(db_full_path)
    cur = con.cursor()
    sql = 'select id, fullpath from music where id=?'
    cur.execute(sql, (id,))
    row = cur.fetchone()
    con.close()
    return row

def group_results(songs, levels_deep=10):
    result = {} if levels_deep > 0 else []
    for song in songs:
        path = song['name']
        parts = path.split(os.sep)
        last = min(len(parts) - 1, levels_deep)
        last = max(last, 0)
        filename = parts[last]
        place = to_nested(result, parts[:last])
        entry = dict(name=filename)
        if entry not in place:
            place.append(entry)
    return result

def to_nested(parent, parts):
    if len(parts) == 0:
        return parent
    k = parts[0]
    if len(parts) == 1:
        if k not in parent:
            parent[k] = []
        return parent[k]
    else:
        if k not in parent:
            parent[k] = {}
        return to_nested(parent[k], parts[1:])

def list_music(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            if file.endswith(('.mp3')):
                fullpath = unicode(os.path.join(dirpath, file), errors='ignore')
                yield fullpath,


#
# term          := [^" ]+
# exact_term    := "(term *)+"
# positive_term := term | exact_term
# negative_term := -(positive_term | negative_term)
# terms         := (positiveterm | negative_term)+
#
# Examples:
# "the beatles" "flaming lips" nirvana -"animal collective" -houston
# "the beatles" -collective
#
class SearchTerm(object):

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
        return 'SELECT id, fullpath FROM music' + self.where_clause()

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
            escaped_value = value.replace("'", "\'")
            return "fullpath LIKE '%" + escaped_value + "%'"
        elif type == 'EXACT':
            return '(' + ' AND '.join([self.term_where_clause(t) for t in value]) + ')'
        elif type in ('POSITIVE', 'NEGATIVE'):
            return self.term_where_clause(value)

            
if __name__ == '__main__':
    for row in search(' '.join(sys.argv[1:])):
        print row
