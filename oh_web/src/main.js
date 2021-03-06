var R = require('ramda');
var $ = require('jquery');
var jss = require('jss');
var home = require('./home');


function assert(cond) {
    if (!cond)
        throw "Assertion failure";
}

function broadcast_handler(path, msg)
{
    console.log("got broadcast: " + path + " => " + msg.toSource());
    var uid = path.replace(/\//g, '-').slice(1);
    for (var key in msg.attrs) {
        var value = msg.attrs[key];
        var keyNode = $(`#${uid}-data > [name=${key}] > [type=key]`).html(key);
        var valNode = $(`#${uid}-data > [name=${key}] > [type=value]`)
            .html(value)
            .css('color', 'green');
        //if (valNode.get(0).timeout !== undefined)
        //    window.clearTimeout(
        //window.setTimeout(() => {node.css('color', 'black')});
    }
}

function attach_data(data, parent) {
    for (var attr in data.attrs) {
        if (attr === 'name' || attr === 'kind')
            continue;

        $(parent).append(`<div name="${attr}">{ <span type="key">${attr}</span>: <span type="value">${data.attrs[attr]}</span> }</div>`);
    }
    if (data.text === undefined)
        return;
    var content = data.text.trim();
    if (content.length > 0)
        $(parent).append(`<div>&lt;text&gt;: ${content}</div>`);
}

function attach_children(tree, parent) {
    $(parent).append("<ul></ul>");
    for (var key in tree.children) {
        var child = tree.children[key];
        var uid = child.path.replace(/\//g, '-').slice(1);
        var p = $(parent)
                    .children()
                    .first().append(
                      $("<li>").attr('id', `${uid}-item`)
                               .addClass('tree-item-style')
                               .addClass(child.data.attrs.kind + '-style').append(
                        $("<span>").html(key)
                      ).append(
                        $("<div>").attr('id', `${uid}-data`)
                      ).append(
                        $("<div>").attr('id', `${uid}-child`)
                      )
                    );

        attach_data(child.data, $(`#${uid}-data`));
        attach_children(child, $(`#${uid}-child`));
    }
    return;
}

function first_component(path) {
    assert(path[0] == '/');
    var parts = path.slice(1).split('/');
    return parts[0];
}

function remainder(path) {
    assert(path[0] == '/');
    var parts = path.slice(1).split('/');
    return '/' + parts.slice(1).join('/');
}

function treeify(path, data, depth) {
    if (depth === undefined)
        depth = 0;

    var keys = R.sort(R.less, R.keys(data));
    if (keys.length === 0)
        return {};

    var children = {}
    var own_data = undefined;
    for (var i = 0; i < keys.length; ++i) {
        var key = keys[i];
        var first = first_component(key);
        var rem = remainder(key);

        if (first === '') {
            own_data = data[key];
        } else {
            if (children[first] === undefined)
                children[first] = {};
            children[first][rem] = data[key];
        }
    }

    for (var key in children)
        children[key] = treeify(`${path}/${key}`, children[key], depth+1);

    return {path: path, children: children, data: own_data};
}

var styles = jss.createStyleSheet({
    'body': {
        'color': '#AAAAAA',
        'background-color': '#000000',
    },
    '.tree-item-style': {
    },
    '.undefined-style': {
        'list-style': 'disc',
    },
    '.home-style': {
        'list-style-image': 'url(/resources/home32.png)',
    },
    '.room-style': {
        'list-style-image': 'url(/resources/room32.png)',
    },
    '.hue-style': {
        'list-style-image': 'url(/resources/hue32.png)',
    },
    '.huebridge-style': {
        'list-style': 'disc',
    },
    '.wemomotion-style': {
        'list-style-image': 'url(/resources/wemomotion32.png)',
    },
    '.wemoswitch-style': {
        'list-style': 'disc',
    },
    '.scene-style': {
        'list-style': 'disc',
    },
});
styles.attach();

home.connect(HOME_ADDRESS, broadcast_handler)
    .then(conn => conn.query('div'))
    .then(msg => {
        //R.map(key => $(target).append(`<div>${key}</div>`), R.keys(msg));
        var tree = treeify('', msg);
        $('body').empty().append('<div id="root">/<div></div></div>');
        attach_children(tree, $("#root > div"));
        //R.map(key => attach(key), keys);
    })
    //.then(R.get('pong'))
    //.then(msg => console.log(msg)); // bug 1105149

