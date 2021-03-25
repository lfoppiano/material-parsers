// var root = (function ($) {

function linkFormatter(value, row) {
    return "<a href='" + row.doc_url + "' target='_blank'>" + row.hash + "</a>";
}

function classesFormatter(value) {
    if (value === undefined || value.length === 0) {
        return "";
    } else {
        return value.join(", ");
    }
}

// function linkFormatter(value, row) {
//     return "<a href='" + row.url + "'>" + row.nice_name + "</a>";
// }

$(document).ready(function () {
    $(function () {
        $('#mainTable').bootstrapTable();
    });

    // $('#toolbar').bind("click", function () {
    //     $('#mainTable').tableExport({type:'csv'});
    // })
});
// })(jQuery);