import os
from pathlib import Path
import re


# Original from https://github.com/tti-coin/sc-comics
from tqdm import tqdm


class ANNParser:
    def __init__(self, data_dir, ignore_rel=False):
        self.data_dir = data_dir
        self.ignore_rel = ignore_rel
        self.doc_info = {}

    def read_ann(self, path):
        with open(path, 'r') as f:
            lines = f.readlines()
        return [l.strip() for l in lines]

    def parse(self):
        data_dir = Path(self.data_dir)
        assert data_dir.is_dir(), '{}: invalid data directory!'.format(
            data_dir)
        self.doc_info = {}  # {file: {tag: ent, rel_info}}
        for ann_path in tqdm(data_dir.glob('*.ann'), desc="Parsing input files"):
            file_name = ann_path.name
            lines = self.read_ann(ann_path)
            txt_path = os.path.join(data_dir, ann_path.stem + '.txt')
            txt = open(txt_path, 'r').read()
            self.doc_info[file_name] = {'text': txt, 'ent': {}, 'rel': {}}

            ent_dict = {}
            for line in lines:
                l_spl = line.split('\t')
                ID = l_spl[0]
                # in case of entity
                if re.match('T', ID):
                    tag, start, end = l_spl[1].split()
                    ent = l_spl[2]
                    ent_info = (ID, int(start), int(end), ent)
                    ent_dict[ID] = (ID, tag, int(start), int(end), ent)
                    if tag not in self.doc_info[file_name]['ent']:
                        # {tag: [id, start, end, entity]}
                        self.doc_info[file_name]['ent'][tag] = [ent_info]
                    else:
                        self.doc_info[file_name]['ent'][tag].append(
                            ent_info)

            if not self.ignore_rel:
                for line in lines:
                    l_spl = line.split('\t')
                    ID = l_spl[0]
                    # in case of relation
                    if re.match('R', ID):
                        tag, arg1, arg2 = l_spl[1].split()
                        arg1 = ent_dict[arg1.split('Arg1:')[1]]
                        arg2 = ent_dict[arg2.split('Arg2:')[1]]
                        rel_info = (ID, arg1, arg2)
                        if tag not in self.doc_info[file_name]['rel']:
                            # {tag: [id, arg1, arg2}
                            self.doc_info[file_name]['rel'][tag] = [
                                rel_info
                            ]
                        else:
                            self.doc_info[file_name]['rel'][tag].append(
                                rel_info)
                    else:
                        pass

        return self.doc_info
