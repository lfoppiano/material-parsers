from operator import itemgetter


class ResolutionResolver(object):
    def link_spans(self, material, tcValue):
        material.ent_type_ = 'material-tc'
        material_links = material._.links
        relationship_link = (tcValue._.id, 'tcValue')
        if relationship_link in material_links:
            print("Link already added. Skipping. Link: " + str(relationship_link))
        else:
            material_links.append(relationship_link)
            material._.set('links', material_links)

        return material, tcValue


class SimpleResolutionResolver(ResolutionResolver):
    def find_relationships(self, entities1: list, entities2: list):
        if len(entities1) == 1 and len(entities2) == 1:
            return [self.link_spans(entities1[0], entities2[0])]
        else:
            return []


class VicinityResolutionResolver(ResolutionResolver):
    separators = [',', '.', ';', 'and']

    ## Assume the entities are already sorted
    def find_relationships(self, doc, entities1, entities2):
        relationships = []

        if len(entities1) < 1 or len(entities2) < 1:
            return relationships

        if len(entities2) == 1:
            closer_material = self.find_closer_to_pivot(entities2[0], entities1)
            relationships.append(self.link_spans(closer_material, entities2[0]))

        elif len(entities1) == 1:
            closer_tcValue = self.find_closer_to_pivot(entities1[0], entities2)
            relationships.append(self.link_spans(entities1[0], closer_tcValue))

        else:
            material_tc_mapping = {}
            tc_material_mapping = {}

            ## Checking that entities1 contains materials, else swap them
            if entities1[0].ent_type_ != "material":
                tmp = entities1
                entities2 = entities1
                entities1 = tmp

            ## If 'respectively' is happearing in the sentence, we need to go in order, rather by absolute distance
            if 'respectively' in str(doc):

                ## Find position and how many 'respectively' are present

                respectively_tokens = [token for token in doc if str(token) == 'respectively']
                if len(respectively_tokens) == 1:
                    relationships.extend(self.assign_in_order(entities1, entities2))
                else:
                    previous_index = 0
                    for respectively_token in respectively_tokens:
                        entities1_reduced = [token for token in entities1 if
                                             respectively_token.i > token.i > previous_index]
                        entities2_reduced = [token for token in entities2 if
                                             respectively_token.i > token.i > previous_index]
                        relationships.extend(self.assign_in_order(entities1_reduced, entities2_reduced))
                        previous_index = respectively_token.i

            else:
                assigned = []
                # for each material I find the closest temperature who has not been assigned yet
                material_tc_mapping = self.calculate_distances(entities1, entities2, doc)

                # build the inverse map tc -> material with each distance
                for material in material_tc_mapping.keys():
                    for tc_val_key in material_tc_mapping[material].keys():
                        if tc_val_key not in tc_material_mapping:
                            tc_material_mapping[tc_val_key] = {material: material_tc_mapping[material][tc_val_key]}
                        elif material not in tc_material_mapping[tc_val_key]:
                            tc_material_mapping[tc_val_key][material] = material_tc_mapping[material][tc_val_key]
                        else:
                            tc_material_mapping[tc_val_key][material] = material_tc_mapping[material][tc_val_key]

                # print(material_tc_mapping)
                # print(tc_material_mapping)

                if len(entities1) <= len(entities2):
                    for material in material_tc_mapping.keys():
                        tc_of_this_material = {tc_: distance for tc_, distance in material_tc_mapping[material].items()
                                               if tc_ not in assigned}

                        tc = min(tc_of_this_material, key=tc_of_this_material.get)
                        if material not in assigned and tc not in assigned:
                            relationships.append(self.link_spans(material, tc))
                            assigned.append(material)
                            assigned.append(tc)
                else:
                    for tc in tc_material_mapping.keys():
                        material_of_this_tc = {material_: distance for material_, distance in
                                               tc_material_mapping[tc].items() if material_ not in assigned}
                        material = min(material_of_this_tc, key=material_of_this_tc.get)
                        if material not in assigned and tc not in assigned:
                            relationships.append(self.link_spans(material, tc))
                            assigned.append(material)
                            assigned.append(tc)

        return relationships

    def assign_in_order(self, entities1, entities2):
        relationships = []
        ## for each material I assign each material to each Tcs, in order of appearance
        if len(entities1) == len(entities2):
            ## Same materials and Tcs, go athead as planned..
            relationships = self.assign_relationship_in_order(entities1, entities2)

        elif len(entities1) > len(entities2):
            ## too many materials, needs to get rid of some of them...
            if entities1[0].idx < entities2[0].idx:
                ## Materials are coming before - remove the head of materials
                relationships = self.assign_relationship_in_order(entities1[-len(entities2):],
                                                                  entities2)
            else:
                ## Materials are coming before - remove the tail of tcs
                relationships = self.assign_relationship_in_order(entities1[0:len(entities2)],
                                                                  entities2)
        else:
            ## Too many tcs
            if entities1[0].idx < entities2[0].idx:
                ## Materials are coming before -> remove the tail of the tcs
                relationships = self.assign_relationship_in_order(entities1,
                                                                  entities2[0:len(entities1)])
            else:
                ## Materials are coming after -> remove the head of tcs
                relationships = self.assign_relationship_in_order(entities1,
                                                                  entities2[-len(entities1):])
        return relationships

    def assign_relationship_in_order(self, entities1, entities2):
        assigned = []
        relationships = []

        if len(entities1) == 0 or len(entities2) == 0:
            return relationships

        for material in entities1:
            material_centroid = material.idx + (len(material) / 2)
            sorted_tcValue = entities2

            if len(entities2) > 1:
                tc_values_wrapper = [(abs(material_centroid - (tc_val.idx + len(tc_val) / 2)), tc_val) for
                                     tc_val in entities2]
                sorted_tcValue_wrapper = sorted(tc_values_wrapper, key=itemgetter(0))
                sorted_tcValue = [tc_val[1] for tc_val in sorted_tcValue_wrapper]

            i = 0
            while i < len(sorted_tcValue) - 1 and sorted_tcValue[i] in assigned:
                i += 1

            if sorted_tcValue[i] not in assigned:
                assigned.append(sorted_tcValue[i])
                assigned.append(material)
                relationships.append(self.link_spans(material, sorted_tcValue[i]))

        return relationships

    def find_previous_entity(self, pivot, items, entity_type=None):
        items_before = [item for item in items if item.idx < pivot.idx]
        if entity_type:
            items_before = [item for item in items_before if item.ent_type_ == entity_type]

        return self.find_closer_to_pivot(pivot, items_before)

    def find_following_entity(self, pivot, items, entity_type=None):
        items_before = [item for item in items if item.idx > pivot.idx]
        if entity_type:
            items_before = [item for item in items_before if item.ent_type_ == entity_type]

        return self.find_closer_to_pivot(pivot, items_before)

    def find_closer_to_pivot(self, pivot, items):
        """Find the closet item from the pivot element"""

        pivot_centroid = pivot.idx + (len(pivot) / 2)
        min_distance = (-1, 0)  # (index_min_distance, distance_value)

        for index, item in enumerate(items):
            item_centroid = item.idx + (len(item) / 2)
            abs_distance = abs(item_centroid - pivot_centroid)

            if index == 0:
                min_distance = (index, abs_distance)
            elif abs_distance < min_distance[1]:
                min_distance = (index, abs_distance)

        if min_distance[0] > -1:
            return items[min_distance[0]]
        else:
            return None

    def calculate_distances(self, materials, tc_values, doc):
        '''
        Calculate the distance between all the elements of source and all the elements of destination:
            - expand the tc length to the wrapping parenthesis (e.g. Material 1 (blabla Tc = 13K) )
            - assign in order without distance assessment if "respectively" is found in the sentence
            - duplicate the distance if a punctuation item is between a couple of material / tc
        '''
        material_tc_mapping = {}
        OPENING_PARENTHESIS = ["(", "[", "{"]
        CLOSING_PARENTHESIS = [")", "]", "}"]
        for index, material in enumerate(materials):
            pivot_centroid = material.idx + (len(material) / 2)

            # If the Tc is present within a parenthesis, I expand the entity to the whole parenthesis itself.
            tc_distances = {}

            for tc_value in tc_values:
                previous_material = self.find_previous_entity(tc_value, materials)
                following_material = self.find_following_entity(tc_value, materials)

                if previous_material is None:
                    previous_material_index = -1
                else:
                    previous_material_index = previous_material.i

                if following_material is None:
                    following_material_index = len(doc)
                else:
                    following_material_index = following_material.i

                # Find out if the opened parenthesis appearing between this tc and the previous material matches
                # the closed parenthesis appearing between this tc and the next material
                any_opened_parenthesis = [item for item in OPENING_PARENTHESIS if
                                          item in str(doc[previous_material_index + 1: tc_value.i - 1])]
                any_closed_parenthesis = [item for item in CLOSING_PARENTHESIS if
                                          item in str(doc[tc_value.i + 1:following_material_index - 1])]

                couple_of_parenthesis = [opened for opened in any_opened_parenthesis if CLOSING_PARENTHESIS[
                    OPENING_PARENTHESIS.index(opened)] in any_closed_parenthesis]

                if len(couple_of_parenthesis) > 0:
                    # doc[previous_material.i + 1: following_material.i - 1].merge()

                    starting_token = [token for token in doc[previous_material_index + 1: tc_value.i - 1] if
                                      str(token) in OPENING_PARENTHESIS][0]
                    ending_token = [token for token in doc[tc_value.i + 1:following_material_index - 1] if
                                    str(token) in CLOSING_PARENTHESIS][-1]

                    tc_distances[tc_value] = abs(pivot_centroid - starting_token.idx +
                                                 len(str(doc[starting_token.i: ending_token.i])) / 2)

                    # Extracting the chunk of text between the material and the updated tcvalue
                    if material.i < tc_value.i:
                        chunk = str(doc[material.i + 1: starting_token.i])
                    else:
                        chunk = str(doc[ending_token.i + 1: material.i])
                else:
                    tc_distances[tc_value] = abs(pivot_centroid - (tc_value.idx + len(tc_value) / 2))
                    if material.i < tc_value.i:
                        chunk = str(doc[material.i + 1: tc_value.i])
                    else:
                        chunk = str(doc[tc_value.i + 1: material.i])

                # Adding penalties in the distances, when the chunk of text in between, contains
                # commas or other punctuation
                if any(item in chunk for item in self.separators):
                    tc_distances[tc_value] *= 2

                material_tc_mapping[material] = tc_distances

        return material_tc_mapping


class DependencyParserResolutionResolver(ResolutionResolver):

    def find_relationships(self, entities1, entities2):
        relations = []
        for entity in entities1:
            if entity.dep_ in ['nsubjpass']:
                relations.append((entity, entity.head))
            elif entity.head.dep_ in ['verb', 'ccomp', 'nsubjpass']:
                if entity.head.dep_ in ['verb', 'ccomp']:
                    relations.append((entity, entity.head))
                elif entity.head.dep_ in ['nsubjpass']:
                    relations.append((entity, entity.head.head))

        output = []
        for entity in entities2:
            if entity.head.dep_ in ['prep', 'pcomp', 'pobj', 'dobj']:
                if entity.head.head.dep_ in ['verb', 'ccomp', 'prep', 'ROOT']:
                    for e, h in relations:
                        if h.idx == entity.head.head.idx:
                            output.append(self.link_spans(e, entity))

        return output

    def find_relationships_with_temperature(self, doc, tcType, entityRelations):
        relations = []
        for entity in filter(lambda w: w.ent_type_ in tcType, doc):
            for rel, ent in entityRelations:
                if entity.head.idx == rel.idx:
                    relations.append((entity.head, ent))
                elif entity.head.head.idx == rel.idx:
                    relations.append((entity.head.head, ent))
        return relations

    def extract_relations2(self, entities1, entities2):
        relations = []
        for entity in entities1 + entities2:
            if entity.dep_ in ("attr", "dobj"):
                subject = [w for w in entity.head.lefts if w.dep_ == "nsubj"]
                if subject:
                    subject = subject[0]
                    relations.append((subject, entity))
            elif entity.dep_ == "pobj" and entity.head.dep_ == "prep":
                relations.append((entity.head.head, entity))
        return relations
