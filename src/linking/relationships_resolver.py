class ResolutionResolver(object):
    pass


class SimpleResolutionResolver(ResolutionResolver):
    def find_relationship(self, doc):
        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc)]

        if len(materials) == 1 and len(tcValues) == 1:
            materials[0].ent_type_ = 'material-tc'
            return [(materials[0], tcValues[0])]
        else:
            return []


class VicinityResolutionResolver(ResolutionResolver):
    separators = [',', '.', ';', 'and']

    def find_relationship(self, doc):
        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc)]

        relationships = []
        assigned = []

        if len(materials) < 1 or len(tcValues) < 1:
            return relationships

        if len(tcValues) == 1:
            closer_material = self.find_closer_to_pivot(tcValues[0], materials)
            closer_material.ent_type_ = 'material-tc'
            relationships.append((closer_material, tcValues[0]))

        elif len(materials) == 1:
            closer_tcValue = self.find_closer_to_pivot(materials[0], tcValues)
            relationships.append((materials[0], closer_tcValue))

        else:
            material_tc_mapping = {}
            tc_material_mapping = {}

            ## If 'respectively' is mention, we need to go in order, rather by absolute distance
            if 'respectively' in str(doc):

                ## for each material I find the closest temperature who has not been assigned yet
                for material in materials:
                    material_centroid = material.idx + (len(material) / 2)
                    sorted_tcValue = tcValues

                    if len(tcValues) > 1:
                        tc_values_wrapper = [(abs(material_centroid - (tc_val.idx + len(tc_val) / 2)), tc_val) for
                                             tc_val in tcValues]
                        sorted_tcValue_wrapper = sorted(tc_values_wrapper, key=itemgetter(0))
                        sorted_tcValue = [tc_val[1] for tc_val in sorted_tcValue_wrapper]

                    i = 0
                    while i < len(sorted_tcValue) - 1 and sorted_tcValue[i] in assigned:
                        i += 1

                    if sorted_tcValue[i] not in assigned:
                        assigned.append(sorted_tcValue[i])
                        material.ent_type_ = 'material-tc'
                        relationships.append((material, sorted_tcValue[i]))

            else:
                # for each material I find the closest temperature who has not been assigned yet
                for index, material in enumerate(materials):
                    material_centroid = material.idx + (len(material) / 2)

                    tc_distances = {tc_val: abs(material_centroid - (tc_val.idx + len(tc_val) / 2)) for tc_val in
                                    tcValues}

                    ## Adding penalties to distance on predicates separated by commas or other punctuation
                    ## If this sentence contains "respectively", it means we should ignore the penalties

                    for tc_val, distance in tc_distances.items():
                        if material.i < tc_val.i:
                            if any(item in str(doc[material.i: tc_val.i]) for item in self.separators):
                                tc_distances[tc_val] *= 2
                        else:
                            if any(item in str(doc[tc_val.i: material.i]) for item in self.separators):
                                tc_distances[tc_val] *= 2

                    material_tc_mapping[material] = tc_distances

                for tc_val_key in material_tc_mapping[list(material_tc_mapping.keys())[0]].keys():
                    for material in material_tc_mapping.keys():
                        if tc_val_key not in tc_material_mapping:
                            tc_material_mapping[tc_val_key] = {material: material_tc_mapping[material][tc_val_key]}
                        elif material not in tc_material_mapping[tc_val_key]:
                            tc_material_mapping[tc_val_key][material] = material_tc_mapping[material][tc_val_key]
                        else:
                            tc_material_mapping[tc_val_key][material] = material_tc_mapping[material][tc_val_key]

                # print(material_tc_mapping)
                # print(tc_material_mapping)

                if len(materials) <= len(tcValues):
                    for material in material_tc_mapping.keys():
                        tc = min(material_tc_mapping[material], key=material_tc_mapping[material].get)
                        if material not in assigned:
                            material.ent_type_ = 'material-tc'
                            relationships.append((material, tc))
                            assigned.append(material)
                else:
                    for tc in tc_material_mapping.keys():
                        material = min(tc_material_mapping[tc], key=tc_material_mapping[tc].get)
                        if material not in assigned:
                            material.ent_type_ = 'material-tc'
                            relationships.append((material, tc))
                            assigned.append(material)

        return relationships

    def find_closer_to_pivot(self, pivot, items):
        """Find the closet item from the pivot element"""

        pivot_centroid = pivot.idx + (len(pivot) / 2)
        min_distance = (-1, 0)  # (index_min_distance, distance_value)

        for index, item in enumerate(items):
            item_centroid = item.idx + (len(item) / 2)
            if abs(item_centroid - pivot_centroid) < min_distance[1]:
                min_distance = (index, abs(item_centroid - pivot_centroid))

        return items[min_distance[0]]


class DependencyParserResolutionResolver(ResolutionResolver):

    def find_relationship(self, doc):
        relations = []
        for entity in filter(lambda w: w.ent_type_ in ['material'], doc):
            if entity.dep_ in ['nsubjpass']:
                relations.append((entity, entity.head))
            elif entity.head.dep_ in ['verb', 'ccomp', 'nsubjpass']:
                if entity.head.dep_ in ['verb', 'ccomp']:
                    relations.append((entity, entity.head))
                elif entity.head.dep_ in ['nsubjpass']:
                    relations.append((entity, entity.head.head))

        output = []
        for entity in filter(lambda w: w.ent_type_ in ['temperature*'], doc):
            if entity.head.dep_ in ['prep', 'pcomp', 'pobj', 'dobj']:
                if entity.head.head.dep_ in ['verb', 'ccomp', 'prep', 'ROOT']:
                    for e, h in relations:
                        if h.idx == entity.head.head.idx:
                            output.append((e, entity))

        return output

    def find_relationship_with_temperature(self, doc, tcType, entityRelations):
        relations = []
        for entity in filter(lambda w: w.ent_type_ in tcType, doc):
            for rel, ent in entityRelations:
                if entity.head.idx == rel.idx:
                    relations.append((entity.head, ent))
                elif entity.head.head.idx == rel.idx:
                    relations.append((entity.head.head, ent))
        return relations

    def extract_relations2(self, doc):
        relations = []
        for entity in filter(lambda w: w.ent_type_ in ['material', 'temperature-tc'], doc):
            if entity.dep_ in ("attr", "dobj"):
                subject = [w for w in entity.head.lefts if w.dep_ == "nsubj"]
                if subject:
                    subject = subject[0]
                    relations.append((subject, entity))
            elif entity.dep_ == "pobj" and entity.head.dep_ == "prep":
                relations.append((entity.head.head, entity))
        return relations
