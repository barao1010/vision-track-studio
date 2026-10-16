# SPDX-License-Identifier: GPL-2.0-or-later
"""Local Bible lookup for licensed/user-supplied verse data.

No translation is bundled or downloaded. Ambiguous quotations remain suggestions.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata


def normalize(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', str(text).lower()) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', text))


BOOKS = [
    ('Gênesis','gn gen genesis'),('Êxodo','ex exodo'),('Levítico','lv lev levitico'),
    ('Números','nm num numeros'),('Deuteronômio','dt deut deuteronomio'),
    ('Josué','js jos josue'),('Juízes','jz juizes'),('Rute','rt rute'),
    ('1 Samuel','1sm 1 samuel primeiro samuel'),('2 Samuel','2sm 2 samuel segundo samuel'),
    ('1 Reis','1rs 1 reis primeiro reis'),('2 Reis','2rs 2 reis segundo reis'),
    ('1 Crônicas','1cr 1 cronicas primeiro cronicas'),('2 Crônicas','2cr 2 cronicas segundo cronicas'),
    ('Esdras','ed esd esdras'),('Neemias','ne neemias'),('Ester','et ester'),('Jó','jo job'),
    ('Salmos','sl salmo salmos'),('Provérbios','pv proverbios'),('Eclesiastes','ec eclesiastes'),
    ('Cânticos','ct canticos cantares cantico dos canticos'),('Isaías','is isaias'),
    ('Jeremias','jr jeremias'),('Lamentações','lm lamentacoes'),('Ezequiel','ez ezequiel'),
    ('Daniel','dn daniel'),('Oseias','os oseias'),('Joel','jl joel'),('Amós','am amos'),
    ('Obadias','ob obadias'),('Jonas','jn jonas'),('Miqueias','mq miqueias'),('Naum','na naum'),
    ('Habacuque','hc habacuque'),('Sofonias','sf sofonias'),('Ageu','ag ageu'),
    ('Zacarias','zc zacarias'),('Malaquias','ml malaquias'),('Mateus','mt mateus'),
    ('Marcos','mc marcos'),('Lucas','lc lucas'),('João','joao jnho'),('Atos','at atos'),
    ('Romanos','rm romanos'),('1 Coríntios','1co 1 corintios primeiro corintios primeira corintios'),
    ('2 Coríntios','2co 2 corintios segundo corintios segunda corintios'),('Gálatas','gl galatas'),
    ('Efésios','ef efesios'),('Filipenses','fp filipenses'),('Colossenses','cl colossenses'),
    ('1 Tessalonicenses','1ts 1 tessalonicenses primeiro tessalonicenses'),
    ('2 Tessalonicenses','2ts 2 tessalonicenses segundo tessalonicenses'),
    ('1 Timóteo','1tm 1 timoteo primeiro timoteo'),('2 Timóteo','2tm 2 timoteo segundo timoteo'),
    ('Tito','tt tito'),('Filemom','fm filemom'),('Hebreus','hb hebreus'),('Tiago','tg tiago'),
    ('1 Pedro','1pe 1 pedro primeiro pedro primeira pedro'),('2 Pedro','2pe 2 pedro segundo pedro segunda pedro'),
    ('1 João','1jo 1 joao primeiro joao primeira joao'),('2 João','2jo 2 joao segundo joao segunda joao'),
    ('3 João','3jo 3 joao terceiro joao terceira joao'),('Judas','jd judas'),('Apocalipse','ap apocalipse')
]
BOOKS += [('Tobias','tob'),('Judite','jdt'),('Ester grego','esg'),('Sabedoria','wis'),
          ('Eclesiástico','sir'),('Baruque','bar'),('1 Macabeus','1ma'),('2 Macabeus','2ma'),
          ('1 Esdras','1es'),('Oração de Manassés','prm'),('Salmo adicional','psx'),
          ('3 Macabeus','3ma'),('4 Esdras','4es'),('4 Macabeus','4ma'),('Daniel grego','dng')]
# Multiword aliases are constructed explicitly, never split into standalone
# 'primeiro' or '1', which would misidentify ordinary sermon words.
ALIASES = {}
for canonical, aliases in BOOKS:
    ALIASES[normalize(canonical)] = canonical
    for token in aliases.split():
        if not token.isdigit() and token not in {'primeiro','primeira','segundo','segunda','terceiro','terceira','dos','cantico'}:
            if canonical[0].isdigit() and token == normalize(canonical).split(' ',1)[1]:
                continue
            if not canonical[0].isdigit(): ALIASES[token] = canonical
    if canonical[0].isdigit():
        number, name = normalize(canonical).split(' ',1)
        for prefix in [number, {'1':'primeiro','2':'segundo','3':'terceiro','4':'quarto'}[number], {'1':'primeira','2':'segunda','3':'terceira','4':'quarta'}[number]]:
            ALIASES[prefix+' '+name] = canonical
        for token in aliases.split():
            if re.fullmatch(r'\d[a-z]+',token): ALIASES[token] = canonical
ALIASES['cantico dos canticos'] = 'Cânticos'
ALIASES['cantares'] = 'Cânticos'


UNITS = dict(zip(['zero','um','dois','tres','quatro','cinco','seis','sete','oito','nove','dez','onze','doze','treze','catorze','quinze','dezesseis','dezessete','dezoito','dezenove'],range(20)))
UNITS.update({'uma':1,'duas':2,'quatorze':14,'dezasseis':16,'dezassete':17,'dezanove':19})
UNITS.update(dict(zip(['vinte','trinta','quarenta','cinquenta','sessenta','setenta','oitenta','noventa'],range(20,100,10))))
UNITS.update({'cem':100,'cento':100,'duzentos':200})


def spoken_numbers(text):
    values=[]
    pending=None
    joined=False
    for token in text.split()[:20]:
        if token=='e' and pending is not None:
            joined=True
            continue
        value=int(token) if token.isdigit() else UNITS.get(token)
        if value is not None:
            if pending is not None and joined:
                pending+=value
            else:
                if pending is not None: values.append(pending)
                pending=value
            joined=False
        else:
            if pending is not None: values.append(pending)
            pending=None
            joined=False
    if pending is not None: values.append(pending)
    return values


@dataclass(frozen=True)
class Verse:
    book: str
    chapter: int
    verse: int
    text: str

    @property
    def title(self):
        return f'{self.book} {self.chapter}:{self.verse}'


class BibleIndex:
    def __init__(self, document):
        if not isinstance(document,dict) or not isinstance(document.get('verses'),list):
            raise ValueError('Bible JSON requires a verses list and translation metadata')
        self.translation = str(document.get('translation','')).strip()
        self.license = str(document.get('license','')).strip()
        if not self.translation or not self.license:
            raise ValueError('Translation and license metadata are required')
        rows=document['verses']
        if not 1 <= len(rows) <= 100000: raise ValueError('Invalid verse count')
        self.verses={}
        self.tokens={}
        self.texts={}
        for row in rows:
            if not isinstance(row,dict): raise ValueError('Invalid verse row')
            book=ALIASES.get(normalize(row.get('book','')))
            chapter, number = row['chapter'],row['verse']
            text=row['text']
            if not book or type(chapter) is not int or type(number) is not int or not 1<=chapter<=150 or not 1<=number<=200 or not isinstance(text,str) or not 1<=len(text)<=5000:
                raise ValueError('Invalid verse')
            key=(book,chapter,number)
            if key in self.verses: raise ValueError('Duplicate verse')
            self.verses[key]=Verse(book,chapter,number,text)
            self.texts[key]=normalize(text)
            for token in set(self.texts[key].split()): self.tokens.setdefault(token,set()).add(key)

    def reference(self, spoken):
        text=normalize(spoken)
        for alias in sorted(ALIASES,key=len,reverse=True):
            match=re.search(r'(?<![a-z0-9])'+re.escape(alias)+r'(?![a-z0-9])',text)
            if not match: continue
            suffix=text[match.end():]
            digits=spoken_numbers(suffix)
            if len(digits)<2: continue
            return self.verses.get((ALIASES[alias],int(digits[0]),int(digits[1])))
        return None

    def quotation(self, spoken, limit=3):
        query=normalize(spoken)
        words=set(query.split())
        if len(words)<4: return []
        candidates=set()
        for token in words: candidates.update(self.tokens.get(token,()))
        scored=[]
        for key in candidates:
            verse=self.verses[key]
            text=self.texts[key]
            tokens=set(text.split())
            overlap=len(words&tokens)/len(words)
            if overlap<.55: continue
            similarity=SequenceMatcher(None,query,text).ratio()
            score=.99 if len(words)>=6 and len(query)>=25 and query in text else .65*overlap+.35*similarity
            if score>=.72: scored.append((score,verse))
        scored.sort(key=lambda item:(-item[0],item[1].title))
        return scored[:max(1,min(int(limit),10))]

    def resolve(self, spoken):
        explicit=self.reference(spoken)
        if explicit: return {'kind':'reference','verse':explicit,'suggestions':[]}
        matches=self.quotation(spoken)
        if not matches: return {'kind':'none','verse':None,'suggestions':[]}
        # Never silently choose among near-identical translations/passages.
        confident=matches[0][0]>=.88 and (len(matches)==1 or matches[0][0]-matches[1][0]>=.08)
        return {'kind':'quotation' if confident else 'ambiguous',
                'verse':matches[0][1] if confident else None,'suggestions':matches}
