const koa = require('koa')
const router = require('koa-router')()
const koaBody = require('koa-body')()
const logger = require('koa-logger')
const cors = require('koa-cors')
const send = require('koa-send')
const request = require('request')

const config = require('./config.json')

const app = koa()

// Global auth config.
let authConfig = {
  accessToken: null,
  expireIn: null,
  now: null
}
// TODO: Hardcoded redirect URL.
const callbackURL = 'http://127.0.0.1:8080'

router.get('/', oauthCode, index)
router.get('/oauth', startOAuth)
router.get('/static/:resource', static)
router.get('/zombies', listZombies)
router.post('/zombies/remove', koaBody, removeZombies)

app
  .use(logger())
  .use(cors())
  .use(router.routes())
  .use(router.allowedMethods())

app.listen(8080)
console.log('Listening on port 8080')


// Handlers.

function* oauthCode(next) {
  if (this.query.code) {
    yield new Promise(resolve => {
      request.post({
        url: 'https://api.weibo.com/oauth2/access_token',
        form: {
          'client_id': config.appKey,
          'client_secret': config.appSecret,
          'redirect_uri': callbackURL,
          'grant_type': 'authorization_code',
          code: this.query.code
        },
        json: true
      }, (err, resp, auth) => {
        // TODO: Error handling.
        authConfig.accessToken = auth['access_token']
        authConfig.expireIn = auth['expires_in']
        authConfig.now = new Date()
        resolve()
      })
    })
    this.redirect('/')
  } else {
    yield next
  }
}

function* index() {
  yield send(this, 'index.html', { root: '../client' })
}

function* startOAuth() {
  const url = 'https://api.weibo.com/oauth2/authorize' +
    `?client_id=${config.appKey}&response_type=code&redirect_uri=${callbackURL}`
  this.redirect(url)
}

function* static() {
  yield send(this, this.params.resource, { root: '../client' })
}

function* listZombies() {
  if (!authConfig.accessToken) {
    this.status = 401
    return
  }

  // TODO: Should be adjustable.
  const limit = 1
  let cursor = 0
  let zombies = []

  while (zombies.length < limit) {
    console.log(cursor, zombies.length)
    yield new Promise(resolve => {
      request.get({
        url: 'https://api.weibo.com/2/friendships/followers.json',
        qs: {
          'access_token': authConfig.accessToken,
          uid: config.uid,
          count: 5,  // TODO: Max.
          cursor
        },
        json: true
      }, (err, resp, data) => {
        // TODO: Error handling.
        cursor = data['next_cursor']
        const followers = data['users']
        for (const f of followers) {
          if (isZombie(f, true)) {  // TODO: Debugging mode.
            zombies.push(f)
          }
        }
        resolve()
      })
    })
  }

  this.body = JSON.stringify(zombies)
}

function* removeZombies() {
  const zombieIds = this.request.body.zombieIds
  if (!zombieIds) {
    this.status = 400
    return
  }
  const removedIds = yield Promise.all(
    zombieIds.map(id =>
      new Promise(resolve => {
        request.post({
          url: 'https://api.weibo.com/2/friendships/followers/destroy.json',
          form: {
            'access_token': authConfig.accessToken,
            uid: id
          },
          json: true
        }, (err, resp, body) => {
          if (err || body.error) {
            console.log(err || body.error)  // TODO
            resolve(-1)  // Will be ignored
          } else {
            console.log(body)  // TODO
            resolve(id)
          }
        })
      })
    )
  )
  this.body = JSON.stringify(removedIds.filter(id => id != -1))
}

// Utility functions.

function isZombie(follower, debug = false) {
  if (debug) {
    return follower['followers_count'] <= 1000
  }

  return follower['followers_count'] <= 1 && follower['statuses_count'] == 0
}
