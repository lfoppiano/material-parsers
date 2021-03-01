// var root = (function ($) {

function linkFormatter(value, row) {
    return "<a href='" + row.sourcepath + "' target='_blank'>" + value + "</a>";
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

// $(document).ready(function () {
$(function () {
    $('#mainTable').bootstrapTable();
});
// $.getJSON('output_sample.json', function (data) {
//     let table = document.getElementById("mainTable")
//     $.each(data, function (key, classes) {
//         let tr = document.createElement("tr")
//         var td1 = document.createElement("td");
//         var td2 = document.createElement("td");
//
//         tr.appendChild(td1);
//         tr.appendChild(td2);
//         table.appendChild(tr);
//
//         let a = document.createElement("a");
//         a.setAttribute("href", "../pdf/" + key);
//         a.append(key)
//         td1.append(a);
//
//         let stringClasses = "";
//         let first = true;
//         for (let clazz in classes) {
//             if (first) {
//                 first = false;
//             }
//             stringClasses += ", " + classes[clazz];
//         }
//
//         td2.append(stringClasses);
//     });
// });

// });
// })(jQuery);