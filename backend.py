import os
from shlex import shlex
import shutil
import time

# if you live in Chelyabinks you can sat it as False
DO_BACKUP = True

class Named:
    class Zone:
        class Record:
            def __init__(self, *args):
                args = [str(i) for i in args]
                self.rd_name, self.rd_ttl, self.rd_class, self.rd_type = args[0:4]
                self.rd_data = ' '.join(args[4:])

            def str(self):
                return '{0:<32} {1:<8} {2:<4} {3:<8} {4}'.format(
                                    self.rd_name, self.rd_ttl, self.rd_class,self.rd_type, self.rd_data)
            def __unicode__(self):
                return unicode(self.str())

            def __repr__(self):
                return self.str()

            def __str__(self):
                return self.str()

        def __init__(self, name, filename):
            self.name = name
            self.filename = filename
            self.records = self.parse()

        def read(self):
            return os.popen('named-checkzone -i none -q -o - %s %s' % (self.name, self.filename)).readlines()

        def parse(self):
            if not self.filename:
                return []
            records = []
            for line in self.read():
                records.append(self.Record(*line.split()))
            return records

        def get_by_name(self, name):
            return [record for record in self.records if record.type.lower() == name.lower()]

        def create_config(self):
            string = ''
            for record in self.records:
                string += str(record)+'\n'
            return string[:-1]

        def write(self):
            if DO_BACKUP:
                folder, filename = os.path.split(self.filename)
                backup_file = os.path.join(folder,self.name,filename+'.'+str(int(time.time())))
                os.makedirs(os.path.join(folder, self.name))
                shutil.move(self.filename, backup_file)
            soa = self.get_by_name('soa')
            split_soa = soa[4].split()
            split_soa[2] = int(time.time())
            fh = open(self.filename,'w')
            fh.write(self.create_config())
            fh.close()

        def __unicode__(self):
            return unicode(self.name)

        def __repr__(self):
            return self.name

        def __str__(self):
            return self.name

    class Statement:
        def __init__(self, name = ''):
            self.items = []
            self.statements = []
            self.current = self
            self.parent = self
            self.name = name

        def split_name(self):
            sp_name = self.name.split(' ')
            if len(sp_name)>0:
                return sp_name
            else:
                return ['', '']

        def append(self, object):
            self.current.items.append(object)
            if object.__class__ == self.__class__:
                self.current.statements.append(object)
                parent = self.current
                self.current = object
                self.current.parent = parent
            if object.__class__ == str().__class__:
                split_object = object.split()
                if len(split_object)>1:
                    setattr(self.current, '_'+split_object[0], ' '.join(split_object[1:]))

        def close(self):
            parent = self.current.parent
            self.current = parent

        def get_statements(self, object = None):
            if not object:
                object = self
            for item in object.statements:
                if item.statements:
                    for gni in self.get_statements(item):
                        yield gni
                yield item


        def get_by_name(self, name):
            return [item for item in self.get_statements() if item.split_name()[0] == name]

        def __unicode__(self):
            return unicode(self.name)

        def __repr__(self):
            return self.name

        def __str__(self):
            return self.name

        def _create_config(self, object = None, depth = 0):
            tmp_str = ''
            skip = False
            if not object:
                object = self
            if str(object.name.find('inet'))=='0': # small hack
                skip = True

            for item in object.items:
                if item.__class__ == self.__class__:
                    tmp_str += item.name + '{ \n'
                    depth += 1
                    tmp_str += self._create_config(item, depth)
                else:
                    tmp_str +=  item + ';\n'
            if skip:
                tmp_str += '} \n'
            else:
                tmp_str += '};\n'
            return tmp_str

        def create_config(self):
            fh = open('tmp.conf', 'w')
            fh.write(self._create_config()[:-4])
            fh.close()
            return os.popen('named-checkconf -p tmp.conf').read()

    def __init__(self):
        self.folder = self.get_config_folder()
        self.config = self.get_config()
        self.statements = self.parse_config()
        self.zones = []
        for zone in self.statements.get_by_name('zone'):
            name = zone.split_name()[1]
            try:
                filename = zone._file
            except AttributeError:
                filename = ''
            self.zones.append(self.Zone(name, filename))


    def get_config_folder(self):
        return [i for i in os.popen('named -V').read().split() if i.find('sysconf')>1][0][1:-1].split('=')[1]

    def get_config(self):
        return os.popen('named-checkconf -p').read()


    def parse_config(self):
        st = self.Statement()
        tokenizer = shlex(self.config)
        tokenizer.wordchars += '/._-'
        tmp_str = ''
        for token in tokenizer:
            if token == '{':
                st.append(self.Statement(tmp_str))
                tmp_str = ''
                continue
            if token == '}':
                st.close()
                tmp_str = ''
                continue
            if token == ';':
                if len(tmp_str)>1:
                    st.append(tmp_str)
                tmp_str = ''
                continue
            tmp_str += ' ' + token
            tmp_str = tmp_str.strip()

        return st

    def write_config(self):
        folder = self.get_config_folder()
        filename = 'named.conf'
        full_path = os.path.join(folder, filename)
        if DO_BACKUP:
            backup_file = os.path.join(folder,filename+'.'+str(int(time.time())))
            shutil.move(full_path, backup_file)
        fh = open(full_path, 'w')
        fh.write(self.statements.create_config())
        fh.close()

if __name__ == '__main__':
    named = Named()
    #print named.statements.items
    named.write_config()
    #print named.zones[7].print_zone()
