import os


class MaterialNER():
    def __init__(self, model_path=None):
        from delft.sequenceLabelling import Sequence
        from delft.sequenceLabelling.models import BidLSTM_CRF

        self.model = Sequence("materialNER-glove_batch_10-BidLSTM_CRF", BidLSTM_CRF.name)
        if model_path and os.path.exists(model_path):
            self.model.load(dir_path=model_path)
        else:
            self.model.load(dir_path="./models")

    def process(self, text: list):
        tags = self.model.tag(text, "json")

        # for text in tags['texts'] if 'texts' in tags else []:

        texts = tags['texts'] if 'texts' in tags else []

        return texts

        #     print("===>>>" + str(tag) + "<<<===")
        #     material = {}
        #     symmetry = ""
        #     sample_descriptor = ""
        #     material_property = ""
        #     material_application = ""
        #     synthesis_method = ""
        #     characterization_method = ""
        #
        #     for entity in tag['entities'] if 'entities' in tag else []:
        #         text = entity['text']
        #         if entity['class'] == "MAT":
        #             material = str(entity['text'])
        #         elif entity['class'] == "SPL":
        #             symmetry = str(entity['text'])
        #         elif entity['class'] == "DSC":
        #             sample_descriptor = str(entity['text'])
        #         elif entity['class'] == "PRO":
        #             material_property = str(entity['text'])
        #         elif entity['class'] == "APL":
        #             material_application = str(entity['text'])
        #         elif entity['class'] == "SMT":
        #             synthesis_method = str(entity['text'])
        #         elif entity['class'] == "CMT":
        #             characterization_method = str(entity['text'])
        #
        #     return {
        #         'material': material,
        #         'symmetry': symmetry,
        #         'sample_descriptor': sample_descriptor,
        #         'material_property': material_property,
        #         'material_application': material_application,
        #         'synthesis_method': synthesis_method,
        #         'characterization_method': characterization_method,
        #     }

# if __name__ == '__main__':
#     pass
