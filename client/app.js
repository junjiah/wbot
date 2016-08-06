$(document).ready(() => {
  // Fetch weibo bots, if not authorized, show the auth form.
  $.get('/zombies')
    .done(onFetchZombiesDone)
    .fail(onFetchZombiesFail)
})

function onFetchZombiesDone(data) {
  var zombies = JSON.parse(data)
  var zombieDiv = $('#zombie-list-div')

  // Create a button.
  var button = $('<a class="button button-black">Remove Zombies</a>')
  button.click(apiRemoveZombies.bind(null, zombies))
  zombieDiv.append(button)
  
  // Build a table.
  var table = '<table><thead><tr><th>Name</th><th>Follower Count</th><th>Weibo Count</th></tr></thead>'
  table += '<tbody>'
  for (var zombie of zombies) {
    var nameEle = `<a href="http://weibo.com/u/${zombie.id}">${zombie['screen_name']}</a>`
    var followerCount = zombie["followers_count"]
    var weiboCount = zombie["statuses_count"]

    var ele = `<tr><td>${nameEle}</td><td>${followerCount}</td><td>${weiboCount}</td></tr>`
    table += ele
  }
  table += '</tbody></table>'
  zombieDiv.append(table)
}

function onFetchZombiesFail(jqXHR) {
  if (jqXHR.status == 401) {
    // Show auth button.
    $('#authorize-button').removeClass('hidden')
  }
}

function apiRemoveZombies(zombies) {
  var ids = zombies.map(z => z.id)
  $.post({
    url: '/zombies/remove', 
    data: { zombieIds: ids },
    dataType: 'json'
  }).done(removedIds => {
    // TODO
    console.log(removedIds)
  })
}
