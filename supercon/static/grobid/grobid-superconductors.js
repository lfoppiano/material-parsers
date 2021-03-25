/**
 *  Javascript functions for the front end.
 *
 *  Borrowed and adapted from https://github.com/kermitt2/grobid
 */

let grobid = (function ($) {

        // for components view
        let responseJson = null;

        let configuration = {};

        function copyTextToClipboard(text) {
            let textArea = document.createElement("textarea");

            //
            // *** This styling is an extra step which is likely not required. ***
            //
            // Why is it here? To ensure:
            // 1. the element is able to have focus and selection.
            // 2. if element was to flash render it has minimal visual impact.
            // 3. less flakyness with selection and copying which **might** occur if
            //    the textarea element is not visible.
            //
            // The likelihood is the element won't even render, not even a
            // flash, so some of these are just precautions. However in
            // Internet Explorer the element is visible whilst the popup
            // box asking the user for permission for the web page to
            // copy to the clipboard.
            //

            // Place in top-left corner of screen regardless of scroll position.
            textArea.style.position = 'fixed';
            textArea.style.top = 0;
            textArea.style.left = 0;

            // Ensure it has a small width and height. Setting to 1px / 1em
            // doesn't work as this gives a negative w/h on some browsers.
            textArea.style.width = '2em';
            textArea.style.height = '2em';

            // We don't need padding, reducing the size if it does flash render.
            textArea.style.padding = 0;

            // Clean up any borders.
            textArea.style.border = 'none';
            textArea.style.outline = 'none';
            textArea.style.boxShadow = 'none';

            // Avoid flash of white box if rendered for any reason.
            textArea.style.background = 'transparent';
            textArea.value = text;

            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            try {
                let successful = document.execCommand('copy');
                let msg = successful ? 'successful' : 'unsuccessful';
                console.log('Copying text command was ' + msg);
            } catch (err) {
                console.log('Oops, unable to copy');
            }

            document.body.removeChild(textArea);
        }

        function copyOnClipboard() {
            console.log("Copying data on clipboard! ");
            let tableResultsBody = $('#tableResultsBody');

            let textToBeCopied = "";

            let rows = tableResultsBody.find("tr");
            $.each(rows, function () {
                let tds = $(this).children();
                for (let i = 2; i < 7; i++) {
                    textToBeCopied += tds[i].textContent
                    if (i < 6) {
                        textToBeCopied += "\t";
                    } else {
                        textToBeCopied += "\n";
                    }
                }
            });
            copyTextToClipboard(textToBeCopied);

        }

        /** Download buttons **/
        function downloadRDF() {
            let fileName = "exportRDF.xml";
            let a = document.createElement("a");
            let xml_header = '<?xml version="1.0"?>';
            let rdf_header = '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:supercon="http://falcon.nims.go.jp/supercuration">';
            let rdf_header_end = '</rdf:RDF>';

            let outputXML = xml_header + "\n" + rdf_header + "\n";

            let tableResultsBody = $('#tableResultsBody');

            let rows = tableResultsBody.find("tr");
            $.each(rows, function () {
                let tds = $(this).children();
                let material = tds[2].textContent;
                let clas = tds[3].textContent;
                let tcValue = tds[4].textContent;
                let pressure = tds[5].textContent;
                let id = $(this).attr("id").replaceAll("row", "");

                outputXML += "\t" + '<rdf:Description rdf:about="http://falcon.nims.go.jp/supercon/' + id + '">';

                outputXML += "\t\t" + '<supercon:material>' + material + '</supercon:material>' + "\n";
                outputXML += "\t\t" + '<supercon:class>' + clas + '</supercon:class>' + "\n";
                outputXML += "\t\t" + '<supercon:tcValue>' + tcValue + '</supercon:tcValue>' + "\n";
                outputXML += "\t\t" + '<supercon:pressure>' + pressure + '</supercon:pressure>' + "\n";

                outputXML += "\t" + '</rdf:Description>';
            });

            outputXML += rdf_header_end;

            let file = new Blob([outputXML], {type: 'application/xml'});
            a.href = URL.createObjectURL(file);
            a.download = fileName;

            document.body.appendChild(a);

            $(a).ready(function () {
                a.click();
                return true;
            });
        }

        function downloadCSV() {
            let fileName = "export.csv";
            let a = document.createElement("a");
            let header = 'material, class, tcValue, applied pressure';
            let outputCSV = header + "\n";

            let tableResultsBody = $('#tableResultsBody');

            let rows = tableResultsBody.find("tr");
            $.each(rows, function () {
                let tds = $(this).children();
                let material = tds[2].textContent;
                let clas = tds[3].textContent;
                let tcValue = tds[4].textContent;
                let pressure = tds[5].textContent;
                // let id = $(this).attr("id").replaceAll("row", "");

                outputCSV += material + ',' + clas + ',' + tcValue + ',' + pressure + "\n";
            });

            let file = new Blob([outputCSV], {type: 'text/csv'});
            a.href = URL.createObjectURL(file);
            a.download = fileName;

            document.body.appendChild(a);

            $(a).ready(function () {
                a.click();
                return true;
            });
        }

        $(document).ready(function () {
            hideResultDivs();

            $('#copy-button').bind('click', copyOnClipboard);
            $('#add-button').bind('click', addRow);
            $('#download-rdf-button').bind('click', downloadRDF);
            $('#download-csv-button').bind('click', downloadCSV);

            // Collapse icon
            $('a[data-toggle="collapse"]').click(function () {
                let currentIcon = $(this).find('img').attr("src")
                let newIcon = currentIcon === chevron_right_path ? chevron_down_path : chevron_right_path;
                $(this).find('img').attr("src", newIcon);
            })

            //turn to inline mode
            $.fn.editable.defaults.mode = 'inline';

            let hash = $("#hash").text();
            processPdf(hash)
        });

        function onError(message) {
            if (!message) {
                message = "The Text or the PDF document cannot be processed. Please check the server logs.";
            } else {
                if (message.responseJSON) {
                    let type = message.responseJSON['type']
                    let split = message.responseJSON['description'].split(type);
                    message = split[split.length - 1]
                } else if (message.type && message.description) {
                    let type = message.type
                    let split = message.description.split(type);
                    message = split[split.length - 1]
                } else {
                    message = "The Text or the PDF document cannot be processed. Please check the server logs. "
                }
            }

            $('#infoResultMessage').html("<p class='text-danger'>Error encountered while requesting the server.<br/>" + message + "</p>");
            return true;
        }

        function cleanupHtml(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        /* jquery-based movement to an anchor, without modifying the displayed url and a bit smoother */
        function goToByScroll(id) {
            console.log("Selecting id " + id.data);
            $('html,body').animate({scrollTop: $("#" + id.data).offset().top - 100}, 'slow');
        }

        function scrollUp() {
            console.log("Scrolling back up");
            $('html,body').animate({scrollTop: 0}, 'slow');
        }


        function hideResultDivs() {
            $('#hash').hide();
            $('#pdf').hide();
            $('#annotations').hide();
            $('#detailed_annot-0-0').hide();
            $('#requestResultPdf').hide();
            $('#requestResultMaterial').hide();
            $('#requestResultLinker').hide();
            $('#requestResultText').hide();
        }

        function processPdf(hash) {
            console.log("Requesting hash: " + hash)
            $('#requestResultPdf').show()
            let requestResult = $('#requestResultPdfContent');
            requestResult.html('');
            requestResult.show();

            $('#tableResultsBody').html('');

            // we will have JSON annotations to be layered on the PDF
            let nbPages = -1;

            let reader = new FileReader();
            reader.onloadend = function () {
                // to avoid cross origin issue
                //PDFJS.disableWorker = true;
                let pdfAsArray = new Uint8Array(reader.result);
                // Use PDFJS to render a pdfDocument from pdf array
                PDFJS.getDocument(pdfAsArray).then(function (pdf) {
                    // Get div#container and cache it for later use
                    let container = document.getElementById("requestResultPdfContent");

                    nbPages = pdf.numPages;

                    // Loop from 1 to total_number_of_pages in PDF document
                    for (let i = 1; i <= nbPages; i++) {

                        // Get desired page
                        pdf.getPage(i).then(function (page) {
                            let table = document.createElement("table");
                            let tr = document.createElement("tr");
                            let td1 = document.createElement("td");
                            let td2 = document.createElement("td");

                            tr.appendChild(td1);
                            tr.appendChild(td2);
                            table.appendChild(tr);

                            let div0 = document.createElement("div");
                            div0.setAttribute("style", "text-align: center; margin-top: 1cm; width:80%;");
                            let pageInfo = document.createElement("p");
                            let t = document.createTextNode("page " + (page.pageIndex + 1) + "/" + (nbPages));
                            pageInfo.appendChild(t);
                            div0.appendChild(pageInfo);

                            td1.appendChild(div0);

                            let scale = 1.5;
                            let viewport = page.getViewport(scale);
                            let div = document.createElement("div");

                            // Set id attribute with page-#{pdf_page_number} format
                            div.setAttribute("id", "page-" + (page.pageIndex + 1));

                            // This will keep positions of child elements as per our needs, and add a light border
                            div.setAttribute("style", "position: relative; ");

                            // Create a new Canvas element
                            let canvas = document.createElement("canvas");
                            canvas.setAttribute("style", "border-style: solid; border-width: 1px; border-color: gray;");

                            // Append Canvas within div#page-#{pdf_page_number}
                            div.appendChild(canvas);

                            // Append div within div#container
                            td1.appendChild(div);

                            let annot = document.createElement("div");
                            annot.setAttribute('style', 'vertical-align:top;');
                            annot.setAttribute('id', 'detailed_annot-' + (page.pageIndex + 1));
                            td2.setAttribute('style', 'vertical-align:top;');
                            td2.appendChild(annot);

                            container.appendChild(table);

                            let context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;

                            let renderContext = {
                                canvasContext: context,
                                viewport: viewport
                            };

                            // Render PDF page
                            page.render(renderContext).then(function () {
                                // Get text-fragments
                                return page.getTextContent();
                            }).then(function (textContent) {
                                // Create div which will hold text-fragments
                                let textLayerDiv = document.createElement("div");

                                // Set it's class to textLayer which have required CSS styles
                                textLayerDiv.setAttribute("class", "textLayer");

                                // Append newly created div in `div#page-#{pdf_page_number}`
                                div.appendChild(textLayerDiv);

                                // Create new instance of TextLayerBuilder class
                                let textLayer = new TextLayerBuilder({
                                    textLayerDiv: textLayerDiv,
                                    pageIndex: page.pageIndex,
                                    viewport: viewport
                                });

                                // Set text-fragments
                                textLayer.setTextContent(textContent);

                                // Render text-fragments
                                textLayer.render();
                            });
                        });
                    }
                }).then(function () {
                    var xhr2 = new XMLHttpRequest();
                    xhr2.open('GET', annotation_url.replaceAll("_HASH_", hash), true);
                    xhr2.responseType = "application/json";
                    xhr2.onreadystatechange = function (e) {
                        if (xhr2.readyState === 4 && xhr2.status === 200) {
                            let response = e.target.response;
                            onSuccessPdf(response)
                        } else if (xhr2.status !== 200) {
                            onError("Response on annotations: " + xhr2.status);
                        }
                    }

                    xhr2.send();
                });
            }

            // request for the annotation information
            var xhr = new XMLHttpRequest();
            xhr.open('GET', pdf_document_url.replaceAll("_HASH_", hash), true);
            xhr.responseType = "blob";
            xhr.onreadystatechange = function (e) {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    var response = e.target.response;
                    reader.readAsArrayBuffer(response);
                } else if (xhr.status !== 200) {
                    onError("Response on PDF: " + xhr.status);
                }
            };

            xhr.send();
        }


        function computeTableIds(id) {
            let row_id = "row" + id;
            let element_id = "e" + id;
            let mat_element_id = "mat" + id;
            let cla_element_id = "cla" + id;
            let shape_element_id = "shape" + id;
            let tc_element_id = "tc" + id;
            let pressure_element_id = "pressure" + id;
            return {
                row_id,
                element_id,
                mat_element_id,
                cla_element_id,
                shape_element_id,
                tc_element_id,
                pressure_element_id
            };
        }

        function onSuccessPdf(response) {
            // TBD: we must check/wait that the corresponding PDF page is rendered at this point
            if ((response == null) || (0 === response.length)) {
                onError("The response is empty.")
                return;
            } else {
                $('#infoResultMessage').html('');
                $('#requestResultPdf').show()
            }

            let json = JSON.parse(response);
            let pages = json['pages'];
            let paragraphs = json['paragraphs'];

            let spanGlobalIndex = 0;
            let copyButtonElement = $('#copy-button');
            let unlinkedElements = [];
            let spansMap = [];


            function encodeLinkAsString(span, link) {
                return [span.id, link.targetId].sort().join("");
            }

            function appendLinkToTable(span, link, addedLinks) {
                let encodedLinkId = encodeLinkAsString(span, link)

                let classes = Object.keys(span.attributes)
                    .filter(function (key) {
                        return key.endsWith("clazz");
                    })
                    .map(function (key) {
                        return span.attributes[key]
                    }).join(", ");

                let shapes = Object.keys(span.attributes)
                    .filter(function (key) {
                        return key.endsWith("shape");
                    })
                    .map(function (key) {
                        return span.attributes[key]
                    }).join(", ");

                let html_code = createRowHtml(encodedLinkId, span.text, link.targetText, link.type, true, cla = classes, shape = shapes);
                let {
                    row_id,
                    element_id,
                    mat_element_id,
                    cla_element_id,
                    shape_element_id,
                    tc_element_id,
                    pressure_element_id
                } = computeTableIds(encodedLinkId);

                if (addedLinks.indexOf(encodedLinkId) >= 0) {
                    let typeRow = $('#' + row_id + " td:eq(7)");
                    let currentType = typeRow.text();
                    currentType += ", " + link.type;
                    typeRow.text(currentType);
                } else {
                    $('#tableResultsBody').append(html_code);
                    addedLinks.push(encodedLinkId)
                }

                // in case of multiple bounding boxes, we will have multiple IDs, in this case we can point
                // to the first box
                $("#" + element_id).bind('click', span.id + '0', goToByScroll);
                $("#" + mat_element_id).editable();
                $("#" + tc_element_id).editable();
                appendRemoveButton(row_id);
                return row_id;
            }

            let globalLinkToPressures = []
            paragraphs.forEach(function (paragraph, paragraphIdx) {
                let addedLinks = []
                let spans = paragraph.spans;
                let localSpans = []
                // hey bro, this must be asynchronous to avoid blocking the brothers

                if (spans) {
                    spans.forEach(function (span, spanIdx) {
                        let annotationId = span.id;
                        spansMap[annotationId] = span;
                        localSpans[annotationId] = span;
                        let entity_type = getPlainType(span['type']);

                        let boundingBoxes = span.boundingBoxes;
                        if ((boundingBoxes != null) && (boundingBoxes.length > 0)) {
                            boundingBoxes.forEach(function (boundingBox, boundingBoxId) {
                                let pageNumber = boundingBox.page;
                                let pageInfo = pages[pageNumber - 1];

                                entity_type = transformToLinkableType(entity_type, span.links);
                                annotateSpanOnPdf(annotationId, boundingBoxId, boundingBox, entity_type, pageInfo);

                                $('#' + (annotationId + '' + boundingBoxId)).bind('click', {
                                    'type': 'entity',
                                    'item': span
                                }, showSpanOnPDF);
                            });
                        }
                        spanGlobalIndex++;
                    });

                    //Extracting pressures and respective tcValue
                    let linkToPressures = []
                    spans.filter(function (span) {
                        return getPlainType(span.type) === "pressure";
                    }).forEach(function (span, spanIdx) {
                        if (span.links !== undefined && span.links.length > 0) {
                            span.links.forEach(function (link, linkIdx) {
                                linkToPressures[link.targetId] = span.id
                                globalLinkToPressures[link.targetId] = span.id
                            });
                        }
                    });


                    spans.filter(function (span) {
                        return getPlainType(span.type) === "material";
                    })
                        .forEach(function (span, spanIdx) {
                            if (span.links !== undefined && span.links.length > 0) {
                                copyButtonElement.show();
                                span.links.forEach(function (link, linkIdx) {
                                        let link_entity = localSpans[link.targetId];
                                        if (link_entity === undefined) {
                                            unlinkedElements.push(span);
                                            return;
                                        }

                                        // span.text == material
                                        // link.targetText == tcValue
                                        let row_id = appendLinkToTable(span, link, addedLinks);
                                        // appendRemoveButton(row_id);

                                        if (linkToPressures[link.targetId] !== undefined) {
                                            $("#" + row_id + " td:eq(6)").text(spansMap[linkToPressures[link.targetId]].text)
                                            delete globalLinkToPressures[link.targetId]
                                        }


                                        let paragraph_popover = annotateTextAsHtml(paragraph.text, [span, link_entity]);

                                        $("#" + row_id).popover({
                                            content: function () {
                                                return paragraph_popover;
                                            },
                                            html: true,
                                            // container: 'body',
                                            trigger: 'hover',
                                            placement: 'top',
                                            animation: true
                                        });
                                    }
                                );
                            }
                        });
                }
            });

            let addedLinks = []

            //Reprocessing the links for which the targetId isn't in the same paragraph
            unlinkedElements.forEach(function (span, spanIdx) {
                if (span.links !== undefined && span.links.length > 0) {
                    span.links.forEach(function (link, linkIdx) {
                        let link_entity = spansMap[link.targetId];
                        if (link_entity === undefined) {
                            console.log("The link to " + link.targetId + " cannot be found. This seems to be a serious problem. Get yourself together. ")
                            return;
                        }

                        // span.text == material
                        // link.targetText == tcValue
                        let row_id = appendLinkToTable(span, link, addedLinks);

                        if (globalLinkToPressures[link.targetId] !== undefined) {
                            $("#" + row_id + " td:eq(6)").text(spansMap[globalLinkToPressures[link.targetId]].text)
                        }

                        $("#" + row_id).popover({
                            content: function () {
                                return "This link is across two sentences, it cannot be previewed for the time being. ";
                            },
                            html: true,
                            // container: 'body',
                            trigger: 'hover',
                            placement: 'top',
                            animation: true
                        });
                    });
                }
            });
        }

        function annotateTextAsHtml(inputText, annotationList) {
            let outputString = "";
            let pos = 0;

            annotationList.sort(function (a, b) {
                let startA = parseInt(a.offsetStart, 10);
                let startB = parseInt(b.offsetStart, 10);

                return startA - startB;
            });

            annotationList.forEach(function (annotation, annotationIdx) {
                let start = parseInt(annotation.offsetStart, 10);
                let end = parseInt(annotation.offsetEnd, 10);

                let type = getPlainType(annotation.type);
                let links = annotation.links
                type = transformToLinkableType(type, links)
                let id = annotation.id;

                outputString += inputText.substring(pos, start)
                    + ' <span id="annot_supercon-' + id + '" rel="popover" data-color="interval">'
                    + '<span class="label ' + type + '" style="cursor:hand;cursor:pointer;" >'
                    + inputText.substring(start, end) + '</span></span>';
                pos = end;
            });

            outputString += inputText.substring(pos, inputText.length);

            return outputString;
        }

        function annotateSpanOnPdf(annotationId, boundingBoxId, boundingBox, type, pageInfo) {
            let page = boundingBox.page;
            let pageDiv = $('#page-' + page);
            let canvas = pageDiv.children('canvas').eq(0);

            // get page information for the annotation
            let page_height = 0.0;
            let page_width = 0.0;
            if (pageInfo) {
                page_height = pageInfo.page_height;
                page_width = pageInfo.page_width;
            }

            let canvasHeight = canvas.height();
            let canvasWidth = canvas.width();
            let scale_x = canvasHeight / page_height;
            let scale_y = canvasWidth / page_width;

            let x = boundingBox.x * scale_x - 1;
            let y = boundingBox.y * scale_y - 1;
            let width = boundingBox.width * scale_x + 1;
            let height = boundingBox.height * scale_y + 1;

            //make clickable the area
            let element = document.createElement("a");
            let attributes = "display:block; width:" + width + "px; height:" + height + "px; position:absolute; top:" +
                y + "px; left:" + x + "px;";
            element.setAttribute("style", attributes + "border:2px solid; box-sizing: content-box;");
            element.setAttribute("class", 'area' + ' ' + type);
            element.setAttribute("id", (annotationId + '' + boundingBoxId));
            element.setAttribute("page", page);

            pageDiv.append(element);
        }

        /** Summary table **/
        function createRowHtml(id, material = "", tcValue = "", type = "", viewInPDF = false, cla = "", shape = "", appliedPressure = "") {

            let viewInPDFIcon = "";
            if (viewInPDF === true) {
                viewInPDFIcon = "<img src='" + arrow_down_path + "' alt='View in PDF' title='View in PDF'></a>";
            }

            let {
                row_id,
                element_id,
                mat_element_id,
                cla_element_id,
                shape_element_id,
                tc_element_id,
                pressure_element_id
            } = computeTableIds(id);

            let html_code = "<tr class='d-flex' id=" + row_id + " style='cursor:hand;cursor:pointer;' >" +
                "<td><a href='#' id=" + element_id + ">" + viewInPDFIcon + "</td>" +
                "<td><img src='"+trash_path+"' alt='-' id='remove-button'/></td>" +
                "<td class='col-3'><a href='#' id=" + mat_element_id + " data-pk='" + mat_element_id + "' data-url='" + '/annotations/feedback' + "' data-type='text'>" + material + "</a></td>" +
                "<td class='col-2'><a href='#' id=" + cla_element_id + " data-pk='" + cla_element_id + "' data-url='" + '/annotations/feedback' + "' data-type='text'>" + cla + "</a></td>" +
                "<td class='col-2'><a href='#' id=" + shape_element_id + " data-pk='" + shape_element_id + "' data-url='" + '/annotations/feedback' + "' data-type='text'>" + shape + "</a></td>" +
                "<td class='col-2'><a href='#' id=" + tc_element_id + " data-pk='" + tc_element_id + "' data-url='" + '/annotations/feedback' + "' data-type='text'>" + tcValue + "</a></td>" +
                "<td class='col-2'><a href='#' id=" + pressure_element_id + " data-pk='" + pressure_element_id + "' data-url='" + '/annotations/feedback' + "' data-type='text'>" + appliedPressure + "</a></td>" +
                "<td class='col-1'>" + type + "</td>" +
                "</tr>";

            return html_code;
        }

        function appendRemoveButton(row_id) {
            let remove_button = $("#" + row_id).find("img#remove-button");
            remove_button.bind("click", function () {
                // console.log("Removing row with id " + row_id);
                let item = $("#" + row_id);
                // Remove eventual popups
                $("#" + item.attr("aria-describedby")).html("").hide();
                item.remove();
            });
        }

        function addRow() {
            console.log("Adding new row. ");

            let random_number = '_' + Math.random().toString(36).substr(2, 9);

            let html_code = createRowHtml(random_number);
            let {
                row_id,
                element_id,
                mat_element_id,
                cla_element_id,
                shape_element_id,
                tc_element_id,
                pressure_element_id
            } = computeTableIds(random_number);

            $('#tableResultsBody').append(html_code);

            $("#" + mat_element_id).editable();
            $("#" + tc_element_id).editable();

            appendRemoveButton(row_id);
        }

        /** Visualisation **/

        function showSpanOnPDF(param) {
            let type = param.data.type;
            let span = param.data.item;

            let pageIndex = $(this).attr('page');
            let string = spanToHtml(span, $(this).position().top);

            if (type === null || string === "") {
                console.log("Error in viewing annotation, type unknown or null: " + type);
            }

            let annotationHook = $('#detailed_annot-' + pageIndex);
            annotationHook.html(string).show();
            //Reset the click event before adding a new one - not so clean, but would do for the moment...
            let scrollUpHook = $('#infobox' + span.id);
            scrollUpHook.off('click');
            scrollUpHook.on('click', scrollUp);
        }

        function transformToLinkableType(type, links) {
            if (links === undefined || links.length === 0) {
                return type;
            }

            if (type === "material") {
                links.forEach(function (link, linkIdx) {
                    if (getPlainType(link['targetType']) === 'tcValue') {
                        type = 'material-tc';
                    }
                });

            } else if (type === "tcValue") {
                links.forEach(function (link, linkIdx) {
                    if (getPlainType(link['targetType']) === 'material') {
                        type = 'temperature-tc';
                    } else if (getPlainType(link['targetType']) === 'pressure') {
                        type = 'temperature-tc';
                    } else if (getPlainType(link['targetType']) === 'me_method') {
                        type = 'temperature-tc';
                    }
                });
            }

            return type;
        }

        function getPlainType(type) {
            return type.replace("<", "").replace(">", "");
        }

        // Transformation to HTML
        function spanToHtml(span, topPos) {
            let string = "";

            //We remove the < and > to avoid messing up with HTML
            let type = getPlainType(span.type);

            let text = span.text;
            let formattedText = span.formattedText;

            string += "<div class='info-sense-box ___TYPE___'";
            if (topPos !== -1)
                string += " style='vertical-align:top; position:relative; top:" + topPos + ";cursor:hand;cursor:pointer;'";
            else
                string += " style='cursor:hand;cursor:pointer;'";

            string += ">";
            if (span.links && topPos > -1) {
                let infobox_id = "infobox" + span.id;
                string += "<h2 class='ml-1' style='color:#FFF;font-size:16pt;'>" + type + "<img id='" + infobox_id + "' src='" + arrow_up_path + "' /></h2>";
            } else {
                string += "<h2 class='ml-1' style='color:#FFF;font-size:16pt;'>" + type + "</h2>";
            }

            string += "<div class='container-fluid border' style='background-color:#FFF;color:#70695C'>";
            // "<table style='width:100%;display:inline-table;'><tr style='display:inline-table;'><td>";

            if (formattedText) {
                string += "<p>name: <b>" + formattedText + "</b></p>";
            } else {
                string += "<p>name: <b>" + text + "</b></p>";
            }

            if (span.links) {
                let colorLabel = transformToLinkableType(type, span.links)
                string = string.replace("___TYPE___", colorLabel);
                let linkedEntities = "";
                let first = true;
                span.links.forEach(function (link, linkIdx) {
                    if (!first) {
                        linkedEntities += ", ";
                    }
                    first = false;
                    linkedEntities += "<b>" + link.targetText + "</b> (" + getPlainType(link.targetType) + ") [" + link.type + "]";

                });
                string += "<p>Linked: " + linkedEntities + "</p>";
            }

            string = string.replace("___TYPE___", type);

            if (span.attributes) {
                let previousPrefix = "";
                let resolvedFormulas = [];
                let formula = "";
                let attributeHtmlString = "<div class='border col-12 p-0'>";
                Object.keys(span.attributes).sort().forEach(function (key) {
                    let splits = key.split("_");
                    let prefix = splits[0];
                    let propertyName = splits[1];

                    if (propertyName === "formula") {
                        formula = span.attributes[key];
                        attributeHtmlString += "<row><div class='col-12'>" + propertyName + ": <strong>" + span.attributes[key] + "</strong></div></row>";
                    } else if (propertyName === 'rawTaggedValue') {
                        //Ignoring

                    } else if (propertyName === 'resolvedFormula') {
                        resolvedFormulas.push(span.attributes[key])
                    } else {
                        attributeHtmlString += "<row><div class='col-12'>" + propertyName + ": <strong>" + span.attributes[key] + "</strong></div></row>";
                    }
                    previousPrefix = prefix;
                });

                if (resolvedFormulas.length > 0 && resolvedFormulas[0] !== formula) {
                    attributeHtmlString += "<row><div class='col-12'>resolvedFormula: <strong>" + resolvedFormulas.join(", ") + "</strong></div></row>";
                }
                attributeHtmlString += "</div>";

                string += attributeHtmlString;
            }

            string += "</div>";
            string += "</div>";

            return string;
        }
    }

)(jQuery);



