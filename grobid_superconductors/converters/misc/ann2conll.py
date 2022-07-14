import argparse
from pathlib import Path
import spacy
from spacy.attrs import ORTH
from collections import Counter
import pandas as pd
from tqdm import tqdm


# Original from https://github.com/tti-coin/sc-comics

def get_args():
    description = ""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("source_dir", type=str,
                        help="")
    parser.add_argument("target_dir", type=str,
                        help="")
    return parser.parse_args()


class ANN2Conll:
    def __init__(self, source_dir, target_dir):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        if not self.target_dir.exists():
            self.target_dir.mkdir(parents=True)

        self.nlp = spacy.load("en_core_sci_sm")
        brackets = [r"\(", r"\)", r"\[", r"]", "{", "}"]
        equals = ["=", "＝", "≠", "≡", "≢", "~", "∼", "≑", "≒", "≓", "≃", "≈", "≔", "≕", "≝", "≜", "⋍", "≅", "˜"]
        ineqals = ["<", ">", "≤", "≥", "≦", "≧", "≪", "≫", "≲", "≳", "≶", "≷", "⋚", "⋛", "⋜", "⋝", "⩽", "⩾", "⪅", "⪆",
                   "⪋", "⪌", "⪍", "⪎", "⪙", "⪚", "＜", "＞", "⋞", "⋟", "⪡", "⪢"]
        hyphens = ["-", "‐", "‑", "–", "—", "―", "−"]
        dashes = ["‒", "–", "—", "―", "⁓", "〜", "〰"]
        props = ["∝", "∼"]
        others = ["!", '"', "#", "$", "%", "&", "'", r"\^", r"\|", "@", r"\:", ";", r"\+", "±", "∓", "/", "_", r"\?",
                  ",", "⊥", "", "‖", "→", "←", "↔", "⇄", "⇒", "⇔"]
        symbols = brackets + equals + ineqals + hyphens + dashes + props + others
        # add prefix pattern
        prefixes = list(self.nlp.Defaults.prefixes)
        prefixes.extend(symbols)
        prefix_regex = spacy.util.compile_prefix_regex(prefixes)
        self.nlp.tokenizer.prefix_search = prefix_regex.search
        # add sufix pattern
        suffixes = list(self.nlp.Defaults.suffixes)
        suffixes.extend(symbols)
        suffixes.append(r"\.")
        suffix_regex = spacy.util.compile_suffix_regex(suffixes)
        self.nlp.tokenizer.suffix_search = suffix_regex.search
        # add infix pattern
        infixes = list(self.nlp.Defaults.infixes)
        infixes.extend(symbols)
        infix_regex = spacy.util.compile_infix_regex(infixes)
        self.nlp.tokenizer.infix_finditer = infix_regex.finditer
        # add special case to tokenizer (BEFORE: "T c." -> "T" "c.", AFTER: "T c." -> "T" "c" ".")
        for l_alph in [chr(i) for i in range(97, 97 + 26)]:
            case = [{ORTH: f"{l_alph}"}, {ORTH: "."}]
            self.nlp.tokenizer.add_special_case(f"{l_alph}.", case)

        self.COUNTS = Counter()

    def read_txt(self, txt_p):
        with txt_p.open("r") as txt_f:
            text = txt_f.read()
        return text

    def read_ann(self, ann_p):
        entities = []
        with ann_p.open("r") as ann_f:
            lines = ann_f.readlines()
        for l in lines:
            if l.startswith("T"):
                tid, label_start_end, mtn = l.strip().split("\t")
                label, start, end = [int(s) if i else s for i, s in enumerate(label_start_end.split())]
                entities.append({"id": tid, "label": label, "start": start, "end": end, "text": mtn})
        return entities

    def get_entities_in_sent(self, sent, entities):
        start, end = sent.start_char, sent.end_char
        res = []
        for ent in entities:
            if start <= ent["start"] and ent["end"] <= end:
                res.append(ent)
        return res

    def align_one(self, sent, ent):
        # Don't distinguish b/w genes that can and can't be looked up in database.
        start_tok = None
        end_tok = None
        for tok in sent:
            if tok.idx == ent["start"]:
                start_tok = tok
            if tok.idx + len(tok) == ent["end"]:
                end_tok = tok

        if start_tok is None or end_tok is None:
            return None
        else:
            expected = sent[start_tok.i - sent.start:end_tok.i - sent.start + 1]
            if expected.text != ent["text"]:
                raise Exception("Entity mismatch")
            return (start_tok.i, end_tok.i, ent["label"])

    def align_entities(self, sent, entities_sent):
        aligned_entities = {}
        missed_entities = {}
        for ent in entities_sent:
            aligned = self.align_one(sent, ent)
            if aligned is not None:
                aligned_entities[ent["id"]] = aligned
            else:
                missed_entities[ent["id"]] = aligned
        return aligned_entities, missed_entities

    def make_conll_lines(self, sent, aligned):
        res = []
        for tok in sent:
            s_idx = tok.idx
            e_idx = s_idx + len(tok)
            text = tok.text

            for a in aligned.values():
                s_tok, e_tok, label = a
                if s_tok <= tok.i <= e_tok:
                    if tok.i == s_tok:
                        line = f"{text} B-{label}"
                    else:
                        line = f"{text} I-{label}"
                    break
            else:
                line = f"{text} O"
            res.append(line)
        return res

    def one_abstract(self, doc_key, text, entities):
        doc = self.nlp(text)
        # import pdb; pdb.set_trace()

        entities_seen = set()
        entities_alignment = set()
        entities_no_alignment = set()

        abst_lines = []
        for sent in doc.sents:
            # Align entities.
            entities_sent = self.get_entities_in_sent(sent, entities)
            aligned, missed = self.align_entities(sent, entities_sent)
            sent_lines = self.make_conll_lines(sent, aligned)
            abst_lines.append(sent_lines)

            # Keep track of which entities and relations we've found and which we haven't.
            entities_seen |= set([ent["id"] for ent in entities_sent])
            entities_alignment |= set(aligned.keys())
            entities_no_alignment |= set(missed.keys())

        # Update counts.
        entities_missed = set([ent["id"] for ent in entities_sent]) - entities_seen

        self.COUNTS["entities_correct"] += len(entities_alignment)
        self.COUNTS["entities_misaligned"] += len(entities_no_alignment)
        self.COUNTS["entities_missed"] += len(entities_missed)
        self.COUNTS["entities_total"] += len(entities)

        return abst_lines

    def format(self):
        ann_files = list(self.source_dir.glob("*.ann"))
        for ann_p in tqdm(ann_files, total=len(ann_files)):
            doc_key = ann_p.stem
            entities = self.read_ann(ann_p)
            text = self.read_txt(ann_p.with_suffix(".txt"))
            abst_lines = self.one_abstract(doc_key, text, entities)

            # Write to file.
            target_p = self.target_dir / f"{doc_key}.conll"
            with open(target_p, "w") as f_out:
                f_out.write("\n\n".join(["\n".join(sent_lines) for sent_lines in abst_lines]))

        counts = pd.Series(self.COUNTS)
        print()
        print("Some entities were missed due to tokenization choices in SciSpacy. Here are the stats:")
        print(counts)


if __name__ == "__main__":
    args = get_args()
    df = ANN2Conll(**vars(args))
    df.format()
