import StringIO
import yaml
import requests


class Definition (object):

    @staticmethod
    def loadRaw (name, args):
        r = requests.get('http://%s:%s/task/define?action=get&file=' % (args.taskhost, args.taskport) + name)
        return StringIO.StringIO(r.text)
    

    @staticmethod
    def loadYaml (name):
        return yaml.safe_load(Definition.loadRaw(name))
        
        
    @staticmethod
    def loadCsv (name, header=True):
        
        reader = csv.reader(Definition.loadRaw(name), delimiter=',', quotechar='"')
        firstRow = header
        
        headRow = []
        rows = []
        
        for row in reader:
            if firstRow:
                headRow = row
                firstRow = False
            else:
                rows.append(row)
       
        return (headRow, rows)

