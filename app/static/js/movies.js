function toggle_visibility(id) {
    if (document.getElementById(id).style.visibility == 'hidden') {
        document.getElementById(id).style.visibility = 'visible';
    }else{
        document.getElementById(id).style.visibility = 'hidden';
    }
}

function delete_movie(movie) {
    var request = new XMLHttpRequest();
    request.open('DELETE', '/movies/delete', false);
    request.setRequestHeader(
        'Content-Type', 
        'application/json;charset=UTF-8'
    );
    request.send(JSON.stringify({'movie': movie}));
    window.location.reload();
}

function put_movie(movie) {
    var request = new XMLHttpRequest();
    request.open('PUT', '/movies/edit', false);
    request.setRequestHeader(
        'Content-Type', 
        'application/json;charset=UTF-8'
    );
    request.send(JSON.stringify({'movie': movie}));
    alert(movie + ' updated');
    window.location.reload();
}
