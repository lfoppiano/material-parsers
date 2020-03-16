/**
 *  Javascript functions for the front end.
 *
 *  Author: Patrice Lopez
 */

var grobid = (function ($) {

        // for components view
        var responseJson = null;

        // for associating several quantities to a measurement
        var spansMap = [];
        var configuration = {};


        function load_configuration() {
            $.ajax({
                type: 'GET',
                url: 'config',
                success: function (data) {
                    configuration = data;
                },
                error: function (error) {
                    onError("Cannot read configuration. " + error);
                },
                contentType: false,
                processData: false
            });
        }


        function getUrl(action) {
            var backend_configuration = configuration['backend'];
            var requestUrl = backend_configuration['server'] + backend_configuration['prefix'];

            if (backend_configuration['url_mapping'][action] !== null) {
                actionUrl = backend_configuration['url_mapping'][action];

                return requestUrl + actionUrl
            } else {
                onError("Action " + action + " was not found in configuration. ");
            }
        }

        $(document).ready(function () {
            $("#divRestI").show();
            $('#tableResults').hide();
            configuration = load_configuration();
            $('#submitRequest').bind('click', 'processPDF', submitQuery);

            //turn to inline mode
            $.fn.editable.defaults.mode = 'inline';
        });

        function onError(message) {
            if (!message)
                message = "The PDF document cannot be annotated. Please check the server logs.";

            $('#infoResult').html("<font color='red'>Error encountered while requesting the server.<br/>" + message + "</font>");
            responseJson = null;
            return true;
        }

        function htmll(s) {
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

        function submitQuery(action) {
            $('#tableResults').hide();
            $('#tableResultsBody').html('');
            spansMap = [];

            $('#infoResult').html('<font color="grey">Requesting server...</font>');
            $('#requestResult').show();
            $('#requestResult').html('');

            // we will have JSON annotations to be layered on the PDF
            var nbPages = -1;
            $('#requestResult').show();

            // display the local PDF
            if ((document.getElementById("input").files[0].type === 'application/pdf') ||
                (document.getElementById("input").files[0].name.endsWith(".pdf")) ||
                (document.getElementById("input").files[0].name.endsWith(".PDF")))
                var reader = new FileReader();
            reader.onloadend = function () {
                // to avoid cross origin issue
                //PDFJS.disableWorker = true;
                var pdfAsArray = new Uint8Array(reader.result);
                // Use PDFJS to render a pdfDocument from pdf array
                PDFJS.getDocument(pdfAsArray).then(function (pdf) {
                    // Get div#container and cache it for later use
                    var container = document.getElementById("requestResult");
                    // enable hyperlinks within PDF files.
                    //var pdfLinkService = new PDFJS.PDFLinkService();
                    //pdfLinkService.setDocument(pdf, null);

                    //$('#requestResult').html('');
                    nbPages = pdf.numPages;

                    // Loop from 1 to total_number_of_pages in PDF document
                    for (var i = 1; i <= nbPages; i++) {

                        // Get desired page
                        pdf.getPage(i).then(function (page) {
                            var table = document.createElement("table");
                            var tr = document.createElement("tr");
                            var td1 = document.createElement("td");
                            var td2 = document.createElement("td");

                            tr.appendChild(td1);
                            tr.appendChild(td2);
                            table.appendChild(tr);

                            var div0 = document.createElement("div");
                            div0.setAttribute("style", "text-align: center; margin-top: 1cm; width:80%;");
                            var pageInfo = document.createElement("p");
                            var t = document.createTextNode("page " + (page.pageIndex + 1) + "/" + (nbPages));
                            pageInfo.appendChild(t);
                            div0.appendChild(pageInfo);

                            td1.appendChild(div0);

                            var scale = 1.5;
                            var viewport = page.getViewport(scale);
                            var div = document.createElement("div");

                            // Set id attribute with page-#{pdf_page_number} format
                            div.setAttribute("id", "page-" + (page.pageIndex + 1));

                            // This will keep positions of child elements as per our needs, and add a light border
                            div.setAttribute("style", "position: relative; ");

                            // Create a new Canvas element
                            var canvas = document.createElement("canvas");
                            canvas.setAttribute("style", "border-style: solid; border-width: 1px; border-color: gray;");

                            // Append Canvas within div#page-#{pdf_page_number}
                            div.appendChild(canvas);

                            // Append div within div#container
                            td1.appendChild(div);

                            var annot = document.createElement("div");
                            annot.setAttribute('style', 'vertical-align:top;');
                            annot.setAttribute('id', 'detailed_annot-' + (page.pageIndex + 1));
                            td2.setAttribute('style', 'vertical-align:top;');
                            td2.appendChild(annot);

                            container.appendChild(table);

                            var context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;

                            var renderContext = {
                                canvasContext: context,
                                viewport: viewport
                            };

                            // Render PDF page
                            page.render(renderContext).then(function () {
                                // Get text-fragments
                                return page.getTextContent();
                            })
                                .then(function (textContent) {
                                    // Create div which will hold text-fragments
                                    var textLayerDiv = document.createElement("div");

                                    // Set it's class to textLayer which have required CSS styles
                                    textLayerDiv.setAttribute("class", "textLayer");

                                    // Append newly created div in `div#page-#{pdf_page_number}`
                                    div.appendChild(textLayerDiv);

                                    // Create new instance of TextLayerBuilder class
                                    var textLayer = new TextLayerBuilder({
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
                });
            };
            reader.readAsArrayBuffer(document.getElementById("input").files[0]);

            // request for the annotation information
            var form = document.getElementById('gbdForm');
            var formData = new FormData(form);
            var xhr = new XMLHttpRequest();
            var url = getUrl(action.data);
            $('#gbdForm').attr('action', url);
            xhr.responseType = 'json';
            xhr.open('POST', url, true);

            xhr.onreadystatechange = function (e) {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    var response = e.target.response;
                    setupAnnotations(response);
                } else if (xhr.status !== 200) {
                    onError("Response: " + xhr.status);
                }
            };
            xhr.send(formData);
        }

        function setupAnnotations(response) {
            // TBD: we must check/wait that the corresponding PDF page is rendered at this point
            if ((response == null) || (0 === response.length)) {
                $('#infoResult')
                    .html("<font color='red'>Error encountered while receiving the server's answer: response is empty.</font>");
                return;
            } else {
                $('#infoResult').html('');
                $('#tableResults').show()
            }

            var json = response;
            var pageInfo = json['pages'];

            var page_height = 0.0;
            var page_width = 0.0;

            var paragraphs = json.paragraphs;

            var spanGlobalIndex = 0;
            var linkId = 0;
            paragraphs.forEach(function (paragraph, paragraphIdx) {
                var spans = paragraph.spans;
                // hey bro, this must be asynchronous to avoid blocking the brothers

                spans.forEach(function (span, spanIdx) {
                    spansMap[span.id] = span;
                    var entity_type = span['type'];

                    var theUrl = null;
                    var boundingBoxes = span.boundingBoxes;
                    if ((boundingBoxes != null) && (boundingBoxes.length > 0)) {
                        boundingBoxes.forEach(function (boundingBox, positionIdx) {
                            // get page information for the annotation
                            var pageNumber = boundingBox.page;
                            if (pageInfo[pageNumber - 1]) {
                                page_height = pageInfo[pageNumber - 1].page_height;
                                page_width = pageInfo[pageNumber - 1].page_width;
                            }
                            // let annotationId = 'annot_span-' + spanIdx + '-' + positionIdx;
                            let annotationId = span.id;
                            annotateSpan(boundingBox, theUrl, page_height, page_width, annotationId, entity_type);
                        });
                    }
                    spanGlobalIndex++;
                });


                spans.forEach(function (span, spanIdx) {
                    if (span.links !== undefined && span.links.length > 0) {
                        span.links.forEach(function (link, linkIdx) {
                            let link_entity = spansMap[link[0]];
                            let tcValue_text = link_entity.text;
                            span['tc'] = tcValue_text;
                            let row_id = 'row' + span.id;
                            let element_id = 'e' + span.id;
                            let mat_element_id = 'mat' + span.id;
                            let tc_element_id = 'tc' + span.id;

                            html_code = "<tr id=" + element_id + " style='cursor:hand;cursor:pointer;' >" +
                                "<td><a href='#' id=" + row_id + "><img src='/static/resources/icons/arrow-down.svg' alt='View in PDF' title='View in PDF'></a></td>" +
                                "<td><a href='#' id=" + mat_element_id + " data-pk='" + mat_element_id + "' data-url='" + getUrl('feedback') + "' data-type='text'>" + span.text + "</a></td>" +
                                "<td><a href='#' id=" + tc_element_id + " data-pk='" + tc_element_id + "' data-url='" + getUrl('feedback') + "' data-type='text'>" + tcValue_text + "</a></td>" +
                                "</tr>";
                            $('#tableResultsBody').append(html_code);

                            $("#" + row_id).bind('click', span.id, goToByScroll);
                            $("#" + mat_element_id).editable();
                            $("#" + tc_element_id).editable();

                            let paragraph_popover = annotateTextAsHtml(paragraph.text, [span, link_entity]);

                            $("#" + element_id).popover({
                                content: function () {
                                    return paragraph_popover;
                                },
                                html: true,
                                // container: 'body',
                                trigger: 'hover',
                                placement: 'top',
                                animation: true
                            });

                            linkId++;
                        });
                    }
                })
            });
        }

        function annotateSpan(boundingBox, theUrl, page_height, page_width, annotationId, type) {
            var page = boundingBox.page;
            var pageDiv = $('#page-' + page);
            var canvas = pageDiv.children('canvas').eq(0);
            //var canvas = pageDiv.find('canvas').eq(0);;

            var canvasHeight = canvas.height();
            var canvasWidth = canvas.width();
            var scale_x = canvasHeight / page_height;
            var scale_y = canvasWidth / page_width;

            var x = boundingBox.x * scale_x - 1;
            var y = boundingBox.y * scale_y - 1;
            var width = boundingBox.width * scale_x + 1;
            var height = boundingBox.height * scale_y + 1;

            //make clickable the area
            var element = document.createElement("a");
            var attributes = "display:block; width:" + width + "px; height:" + height + "px; position:absolute; top:" +
                y + "px; left:" + x + "px;";
            element.setAttribute("style", attributes + "border:2px solid;");
            element.setAttribute("class", 'area' + ' ' + type);
            element.setAttribute("id", annotationId);
            element.setAttribute("page", page);

            pageDiv.append(element);

            $('#' + annotationId).bind('click', {
                'type': 'entity',
                'map': spansMap
            }, viewEntityPDF);
        }


        function viewEntityPDF(param) {
            var type = param.data.type;
            var map = param.data.map;

            var pageIndex = $(this).attr('page');
            var id = $(this).attr('id');

            if ((map[id] === null) || (map[id].length === 0)) {
                // this should never be the case
                console.log("Error for visualising annotation with id " + id
                    + ", empty list of measurement");
            }
            var string = toHtmlEntity(map[id], $(this).position().top);

            if (type === null || string === "") {
                console.log("Error in viewing annotation, type unknown or null: " + type);
            }

            $('#detailed_annot-' + pageIndex).html(string).show();
            $('#detailed_annot-' + pageIndex).bind('click', scrollUp);
        }

        function annotateTextAsHtml(inputText, annotationList) {
            var outputString = "";
            var pos = 0;

            annotationList.sort(function (a, b) {
                var startA = parseInt(a.offsetStart, 10);
                var startB = parseInt(b.offsetStart, 10);

                return startA - startB;
            });

            annotationList.forEach(function (annotation, annotationIdx) {
                var start = parseInt(annotation.offsetStart, 10);
                var end = parseInt(annotation.offsetEnd, 10);

                var type = annotation.type;

                outputString += inputText.substring(pos, start)
                    + ' <span id="annot_supercon-' + annotationIdx + '" rel="popover" data-color="interval">'
                    + '<span class="label ' + type + ' style="cursor:hand;cursor:pointer;" >'
                    + inputText.substring(start, end) + '</span></span>';
                pos = end;
            });

            outputString += inputText.substring(pos, inputText.length);

            return outputString;
        }


        // Transformation to HTML
        function toHtmlEntity(entity, topPos) {
            var string = "";
            var first = true;

            colorLabel = entity.type;
            var text = entity.text;
            var formattedText = entity.formattedText;
            var type = entity.type;

            string += "<div class='info-sense-box ___TYPE___'";
            if (topPos !== -1)
                string += " style='vertical-align:top; position:relative; top:" + topPos + ";cursor:hand;cursor:pointer;'";
            else
                string += " style='cursor:hand;cursor:pointer;'";

            string += ">";
            if (entity.tc) {
                var infobox_id = "infobox" + entity.id;
                string += "<h2 style='color:#FFF;padding-left:10px;font-size:16pt;'>" + type + "<img id='" + infobox_id + "' src='/static/resources/icons/arrow-up.svg'/></h2>";

            } else {
                string += "<h2 style='color:#FFF;padding-left:10px;font-size:16pt;'>" + type + "</h2>";
            }

            string += "<div class='container-fluid' style='background-color:#FFF;color:#70695C;border:padding:5px;margin-top:5px;'>" +
                "<table style='width:100%;display:inline-table;'><tr style='display:inline-table;'><td>";

            if (formattedText) {
                string += "<p>name: <b>" + formattedText + "</b></p>";
            } else {
                string += "<p>name: <b>" + text + "</b></p>";
            }

            if (entity.tc) {
                string += "<p>Tc: <b>" + entity.tc + "</b></p>";
                string = string.replace("___TYPE___", "material-tc");
            }
            string = string.replace("___TYPE___", type);

            string += "</td></tr>";
            string += "</table></div>";

            string += "</div>";

            return string;
        }
    }

)(jQuery);



