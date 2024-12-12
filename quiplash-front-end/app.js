'use strict';

// Import express and process
const express = require('express');
const { listenerCount, disconnect, send } = require('process');
const app = express();

// Setup socket.io for Server-Client Communication
const server = require('http').Server(app);
const io = require('socket.io')(server);

// Key-Value Maps for users connected to the server:
let users = new Map();
// [ username, { username, state: [0-9], games_played, round_score, total_score, role: ["ADMIN/PLAYER/AUDIENCE"], promptQ1, promptQ2, current_prompt} ]

let usersToSockets = new Map(); // username -> user's socket
let socketsToUsers = new Map(); // user's socket -> username

let admin_name = null; // Storing the username of the admin
let podium = null;

// Display client
let display_client_socket = null;

// Key-Value Maps for the prompts
let local_Prompts = []; // Prompts written in the CURRENT GAME.
let API_Prompts = []; // Prompts from the API.
let round_Prompts = []; // Prompts to be used in A ROUND
let promptToAnswers = new Map(); // Representing the answers from two players:
// { prompt, { answers: [ { username: "username", answer: "answer", votes: 0}, ... ] } }
let promptToAnswersIt = null; // Iterator for promptToAnswers Map
let currentPromptToAnswer = null;
let previousRoundPromptToAnswers = new Map();


// Server's current state
let server_state = { state: 0, round: 0, prompt_vote: null, leaderboard: {} };
// server_state.state -> 0: Lobby, 1: Prompt, 2: Answers, 3: Voting, 4: Vote results, 5: Round Scores, 6: Game Over
// prompt_vote: Value of current currentPromptToAnswer


// Setup static page handling
app.set('view engine', 'ejs');
app.use('/static', express.static('public'));
app.get('/', (req, res) => {
  // client.ejs
  res.render('client'); 
});

// URL of the backend API
const LOCAL_DEV_URL = "http://localhost:8181"
const PUBLIC_URL = null
const TEST_URL = LOCAL_DEV_URL
const BACKEND_ENDPOINT = process.env.BACKEND || TEST_URL;

// Start the server, listens on port 8080 OR the PORT environment variable.
function startServer() {
    const PORT = process.env.PORT || 8080;
    server.listen(PORT, () => {
        console.log(`Server listening on port ${PORT}`);
    });
}


// Update state of all users and display if any.
function updateAll() {
  console.log('Updating all users');
  for (let [username,socket] of usersToSockets) {
    updateUser(socket);
  }

  const data = { server_state: server_state, users: Object.fromEntries(users), user_count: users.size, podium: podium, url: TEST_URL };
  updateDisplayClient('update-display',data);
}


// Update display client.
function updateDisplayClient(command, data) {
  if (display_client_socket == null) return;
  display_client_socket.emit(command, data);
}

// Update one user's state.
function updateUser(socket) {
  const username = socketsToUsers.get(socket);
  const theUser = users.get(username);
  const data = { server_state: server_state, user_state: theUser, 
    users: Object.fromEntries(users), user_count: users.size, podium: podium };
  socket.emit('update-user', data);
}

// Handle a user leaving the server.
function handleQuit(socket) {
  if (!socketsToUsers.has(socket)) {
    console.log('Handling quit');
    return;
  }
  const username = socketsToUsers.get(socket);
  const theUser = users.get(username);
  // Assign a new admin from users list before removing the user from the maps.
  if (theUser.role == "ADMIN") {
    for (let [username,user] of users) {
      if (user.role == "PLAYER") { 
        editUser(username,"ADMIN");
        admin_name = username;
        break;
      }
    } 
  } 
  removeUser(socket)
}


// Handle a player registering with /player/register API function.
async function handleRegister(socket, username, password) {
  const json_body = { username: username, password: password, };
  const data = await requestBackend('/player/register', 'POST', json_body);
  // Send the API response to client.
  socket.emit('register-response', data.msg);
}


// Handle a player logging in with /player/login API function.
async function handleLogin(socket, username, password) {
  const json_body = { username: username, password: password, };
  const data = await requestBackend('/player/login', 'POST', json_body);
  // Send the API response to client.
  socket.emit('login-response', data.msg)
}


// Handle a player joining the game.
function handleJoin(socket, username) {
  // Update the user's state if they joined late (automatically an audience member):
  if (server_state.state > 0 && server_state.state < 6) {
    addUser(socket,username,"AUDIENCE");
    switch (server_state.state) {
      case 1:
        users.get(username).state = 1; // Allow audience members to write prompts if players are still writing prompts.
        break;
      case 2:
        users.get(username).state = 4; // User needs to wait for players to finish answering prompts.
        break;
      case 3:
        users.get(username).state = 5; // Wait for the current votes.
        break;
      case 4:
        users.get(username).state = 7; // Viewing the current votes.
        break;
      case 5:
        users.get(username).state = 8; // Viewing the round scores.
        break;
      case 6:
        users.get(username).state = 9; // GAME OVER.
        break;
    }
  } else {

    // Reset server state if a game happened already.
    if (server_state.state == 6) {
      server_state = { state: 0, round: 0, prompt_vote: null };
    }

    // Assign the roles if the game hasn't started yet.
    if (users.size == 0) {
    addUser(socket,username,"ADMIN");
    admin_name = username;
    } else if (0 < users.size && users.size < 8 ) {
      addUser(socket,username,"PLAYER");
    } else if (users.size >= 8){
      addUser(socket,username,"AUDIENCE");
    }
  }
}


// Add a user along with their role to the User Maps:
function addUser(socket, username, role) {
  users.set(username, { username: username, state: 0, games_played: 0, round_score: 0, total_score: 0, role: role, promptQ1: null, promptQ2: null, current_prompt: null});
  usersToSockets.set(username, socket);
  socketsToUsers.set(socket,username);
  console.log('[' + role +']: ' + username + ' joined the game, user count = ' + users.size );
}


// Edit a user's role:
function editUser(username, role) {
  const theUser = users.get(username);
  console.log("Editing " + theUser.username + "'s role: " + theUser.role + " -> " + role);
  theUser.role = role;
}


// Remove a user from the server by removing from ALL User Maps:
function removeUser(socket) {
  const username = socketsToUsers.get(socket);
  const role = users.get(username).role;
  socketsToUsers.delete(socket);
  usersToSockets.delete(username);
  users.delete(username)
  console.log('[' + role +']: ' + username + ' left the game, user count = ' + users.size );
}


// Handle an admin's actions:
function handleAdmin(socket,action) {
  const username = socketsToUsers.get(socket)
  const theUser = users.get(username)
  if (theUser.role != 'ADMIN') {
    // Mitigate any non-admins doing admin actions
    console.log('[' + theUser.role +']: ' + username + ' attempted the admin action ' + action + ' [FAILED]');
    return;
  }
  if(action == 'start' && server_state.state == 0) { // Start the Game.
    startRound();
  } else if (action == 'finish-prompts' && server_state.state == 1) {
    endPrompts();
  } else if (action == 'finish-answers' && server_state.state == 2) {
    endAnswers();
  } else if (action == 'finish-vote' && server_state.state == 4) { // Go to NEXT prompt vote OR show round scores.
    updateVote();
  } else if (action = 'finish-round-scores' && server_state.state == 5) { // Transition to next Round/Game Over.
    endScores();
  } else {
    console.log('Unknown admin action: ' + action) // Invalid admin action.
  }
}

// Initalise a Game Round
function startRound() {
  server_state.round ++;
  if (server_state.round > 3) {
     // Terminate game once round 3 is over.
     console.log('Game Over!');
     startGameOver();
  } else {
    // Start the prompt writing round.
    console.log('Round ' + server_state.round + ' starting...');
    startPrompts();
  }
}


// Show Game over screen
async function startGameOver() {
  // Prepare the leaderboardcand final scores
  server_state.state = 6;

  // Update the podium and scores
  await updateScoresToDB();
  podium = await getPodium();

  // Show the users the final screen
  for (const [username,user] of users) {
    user.state = 9;
  }
  updateAll();
}

// Get the podium with the /utils/podium API function.
async function getPodium() {
  console.log('Getting Podium...');
  return await requestBackend('/utils/podium', 'POST', {});
}


// Update everyone's scores to the database.
async function updateScoresToDB() {
  for (const [username,user] of users) {
    const json_body = {username: username , add_to_games_played: 1 , add_to_score : user.total_score }
    await requestBackend('/player/update/', 'PUT', json_body);
  }
}


function startPrompts() {
  // Change server state to prompt stage.
  console.log('Everyone will now suggest some prompts...');
  server_state.state = 1;
  updateDisplayClient('reset-prompt-display');
  // Update all player's state for "Writing 1st prompt".
  for (const [username,user] of users) {
    user.state = 1;
    const socket = usersToSockets.get(username);
    socket.emit('reset-prompt-state');
  }
}


// Handle the prompt creation by a player.
async function handleSubmitPrompt(socket, prompt) {
  const username = socketsToUsers.get(socket);

  // Add to list of prompts written in the current round.
  local_Prompts.push(prompt);

  // Add to database with /prompt/create API function.
  const json_body = { text: prompt, username: username, };
  const data = await requestBackend('/prompt/create', 'POST', json_body);

  // Update player state once the prompt is valid:
  if (data.msg == 'OK') {
    const theUser = users.get(username);
    theUser.state = 2;
    updateUser(socket);
    updateDisplayClient('increment-prompt-count', username);
  }

  socket.emit('prompt-response', data.msg);

  // Move to "Answering Prompt" Stage if all players submitted at least one prompt. 
  if (allUsersInSameState(2)) {
    console.log('Waiting for admin...');
    sendToAdmin('prompt-response', 'OK, all players answered');
  }
}

// Send message directly to admin
function sendToAdmin(listener_message, message) {
  const adminSocket = usersToSockets.get(admin_name);
  adminSocket.emit(listener_message, message);
}

// Check if all users are in the same state
function allUsersInSameState(i) {
  for (const [username,user] of users) {
    if (user.state != i) {
      return false;
    }
  }
  return true;
}


// Terminate "Writing Prompt" stage
function endPrompts() {
  console.log('Players will now answer the prompts...');
  server_state.state = 2;
  getAPIPrompts();
}


// Add the API prompts with the /utils/get API function.
async function getAPIPrompts() {
  // Get ALL user prompt history.
  let userList = Array.from(users.keys());
  const json_body = { players: userList, language: "en" }; 
  const data = await requestBackend('/utils/get', 'POST', json_body); // API request

  // Only get the english translations for now.
  API_Prompts = data.flatMap(item =>
    item.texts
      .filter(textObj => textObj.language === "en")
      .map(textObj => textObj.text)
  );

  // Sort the local and API prompts to the 50/50 split.
  getRoundPrompts();
}


// Shuffle list
function shuffleList(list) {
  for (let i = list.length - 1; i > 0; i--) {
    // Generate a random index from 0 to i
    const randomIndex = Math.floor(Math.random() * (i + 1));
    // Swap elements at i and randomIndex
    [list[i], list[randomIndex]] = [list[randomIndex], list[i]];
  }
  return list;
}


// Sort the prompts to be used in the current round.
function getRoundPrompts() {
  // Collect all the players.
  let players = new Map(
    [...users].filter(([username, user]) => user.role != "AUDIENCE")
  );
  console.log("Players: " + Array.from(players.keys()));

  // Both prompt lists are mutually exclusive.
  API_Prompts = API_Prompts.filter(item => !local_Prompts.includes(item));

  // Remove the prompts already used in previous rounds of the current game.
  let used_prompts = Array.from(previousRoundPromptToAnswers.keys());
  API_Prompts = API_Prompts.filter(item => !used_prompts.includes(item));
  local_Prompts = local_Prompts.filter(item => !used_prompts.includes(item));

  // Shuffle prompt lists:
  API_Prompts = shuffleList(API_Prompts);
  local_Prompts = shuffleList(local_Prompts);

  // Get the randomised 50/50 split of API and local prompts (Prioritise the local ones).
  for (let i = 0; i < players.size; i++) {
    round_Prompts.push(local_Prompts[i]);
    round_Prompts.push(API_Prompts[i]);
  }

  // Now assign the prompts.
  startAnswers(players);
}

// Assign prompts dppending one the number of players.
function startAnswers(players) {
  if (players.size % 2 === 0) {
    // Assign the even players
    console.log("There are an even number of players...");
    round_Prompts = round_Prompts.slice(0, players.size / 2);
    round_Prompts = shuffleList(round_Prompts);
    console.log("Round Prompts: " + round_Prompts);

    let i = 0; // index for prompts
    let j = 1; // player number
    for (let [username, player] of players ) {
      player.state = 3;
      player.current_prompt = round_Prompts[i];
      
      // Go to next prompt in the prompt list when this is the n-th player, when n is even
      if (j % 2 === 0) { 
        promptToAnswers.set(round_Prompts[i], {answers: []} );
        i++; 
      }
      j++;

      updateDisplayClient('add-player-whos-answering',username);
    }
  } else {
    // Assign the odd players
    console.log("There are an odd number of players...");
    round_Prompts = round_Prompts.slice(0, players.size);
    round_Prompts = shuffleList(round_Prompts);
    console.log("Round Prompts: " + round_Prompts);

    // The second prompt will be from the same list but shifted to the left by 1.
    // This is so the players will get two different prompts per round.
    let i = 0; // Prompt index
    for (let [username, player] of players ) {
      player.state = 3;
      player.promptQ1 = round_Prompts[i];
      player.current_prompt = player.promptQ1;
      promptToAnswers.set(round_Prompts[i], {answers: []} );
      if (i < players.size - 1) {
        player.promptQ2 = round_Prompts[i + 1];
      } else {
        player.promptQ2 = round_Prompts[0];
      }
      i++;

      updateDisplayClient('add-player-whos-answering',username);
    }
  }


  // Put the audience in a waiting screen.
  let audience = new Map(
    [...users].filter(([username, user]) => user.role == "AUDIENCE")
  );
  for (let [username,audience_member] of audience) {
    audience_member.state = 4;
  }
  updateAll();
}


// Handle submitted answers.
function handleSubmitAnswer(socket, prompt, answer) {
  // Add to the promptToAnswers Map.
  const playername = socketsToUsers.get(socket);
  const thePlayer = users.get(playername);
  const thePrompt = promptToAnswers.get(prompt);
  thePrompt.answers.push({ username: playername, answer: answer, votes: [] })

  // Take them to the next prompt if their promptQ1 is set.
  if (thePlayer.promptQ1 == prompt) {
    thePlayer.current_prompt = thePlayer.promptQ2;
  } else {
    // Reset their prompt states and put them in the waiting state when they finish.
    thePlayer.current_prompt = null;
    thePlayer.promptQ1 = null;
    thePlayer.promptQ2 = null;
    thePlayer.state = 4;
    updateDisplayClient('add-player-whos-answered',playername);
  }

  // Move to next game state if all players submitted a prompt.
  if (allUsersInSameState(4)) {
    console.log('Waiting for admin...');
    sendToAdmin('prompt-response', 'OK, all players answered the prompts');
  }
}


// Go over the answered prompts and ask for everyone to vote.
function endAnswers() {
  console.log('Everyone will now vote the prompt answers...');
  server_state.state = 3;
  
  // Initalise the iterator
  promptToAnswersIt = promptToAnswers.entries();
  currentPromptToAnswer = promptToAnswersIt.next();
  startVoting();
}

function startVoting() {
  // { "prompt", { answers: [{username: "username", answer: "answer", votes: 0}, ... ]} } promptToAnswers
  // { prompt: "prompt", { player_1: {username: "username", answer: "answer"}, ... ]} } server

  let [key, value] = currentPromptToAnswer.value;
  console.log('Current Prompt: ' + key);

  // Send the prompts to the voters.
  const player_1 = value.answers[0];
  const p1_info = { username: player_1.username, answer: player_1.answer, votes: player_1.votes };
  const player_2 = value.answers[1];
  const p2_info = { username: player_2.username, answer: player_2.answer, votes: player_2.votes };

  server_state.prompt_vote = { prompt: key, player_1: p1_info, player_2: p2_info };

  for (const [username,user] of users) {
    user.state = 5;
  }

  // Put those players in the waiting state.
  users.get(player_1.username).state = 6;
  users.get(player_2.username).state = 6;
}


// Handle sent votes for a prompt.
function handleSubmitVote(socket, prompt, username) {
  // { "prompt", { answers: [{username: "username", answer: "answer", votes: 0}, ... ]} } promptToAnswers
  const thePrompt = promptToAnswers.get(prompt);
  const answers = thePrompt.answers;

  // Update the voter's state
  const theVoterName = socketsToUsers.get(socket);
  const theVoter = users.get(theVoterName);

  // Assign the vote to the player
  switch (username) {
    case answers[0].username:
      answers[0].votes.push(theVoterName);
      console.log(theVoterName + ' voted for ' + answers[0].username + '! Vote count: ' + answers[0].votes.length + ', Votes: ' + answers[0].votes);
      break;
    case answers[1].username:
      answers[1].votes.push(theVoterName);
      console.log(theVoterName + ' voted for ' + answers[1].username + '! Vote count: ' + answers[1].votes.length + ', Votes: ' + answers[1].votes);
      break;
  }

  // Let the users who already voted in the waiting state.
  theVoter.state = 6;

  // Check if all users have voted and move to next state.
  if (allUsersInSameState(6)) {
    // Show the results of the voting.
    console.log('Voting now finished!');
    startVoteResults();
  }
}


// If there are multiple votes, move on to the next one. If not, end the round.
function updateVote() {
  let next_prompt = promptToAnswersIt.next();
  currentPromptToAnswer = next_prompt;

  if (!next_prompt.done) {
    // Do next prompt
    console.log('Moving on to next prompt');
    startVoting();
  } else {
    endVoting();
  }
}


// Transition to the vote results.
function startVoteResults() {
  // Update the server's prompt_vote
  let [key, value] = currentPromptToAnswer.value;

  // Add up the round scores for each player.
  const player_1 = value.answers[0];
  let p1_info = { username: player_1.username, answer: player_1.answer, votes: player_1.votes, vote_count: player_1.votes.length };
  const thePlayer_1 = users.get(player_1.username);
  const score_1 = (server_state.round * p1_info.vote_count * 100);
  thePlayer_1.round_score += score_1;
  console.log(player_1.username + " gained " + score_1 + " round points!");

  const player_2 = value.answers[1];
  let p2_info = { username: player_2.username, answer: player_2.answer, votes: player_2.votes, vote_count: player_2.votes.length };
  const thePlayer_2 = users.get(player_2.username);
  const score_2 = (server_state.round * p2_info.vote_count * 100);
  thePlayer_2.round_score += score_2;
  console.log(player_2.username + " gained " + score_2 + " round points!");

  p1_info = { username: player_1.username, answer: player_1.answer, votes: player_1.votes, vote_count: player_1.votes.length, round_score: score_1 };
  p2_info = { username: player_2.username, answer: player_2.answer, votes: player_2.votes, vote_count: player_2.votes.length, round_score: score_2 };

  server_state.prompt_vote = { prompt: key, player_1: p1_info, player_2: p2_info };

  // Display the votes
  server_state.state = 4;
  for (const [username,user] of users) {
    user.state = 7;
  }
  console.log('Showing Vote results for Prompt: ' + key);
}


// Show the score screen.
function endVoting() {
  console.log('Showing Scores...');

  // Add to their total score and show the scores.
  server_state.state = 5;
  for (const [username,user] of users) {
    if (user.role != 'AUDIENCE') {
      const original_total = user.total_score;
      user.total_score += user.round_score;
      console.log(username + ": " + original_total + " + " + user.round_score);
    }
    user.state = 8;
  }

  // Update the leaderboard.
  let players = new Map(
    [...users].filter(([username, user]) => user.role != "AUDIENCE")
  );

  const leaderboard = [...players].sort((a, b) => b[1].total_score - a[1].total_score);
  server_state.leaderboard = leaderboard;
  
  console.log('Leaderboard:')
  for (const [username,user] of server_state.leaderboard) {
    console.log(username + ": " + user.total_score);
  }
  
}

function endScores() {
  // Show the scores
  server_state.state = 1;

  // Reset the round score.
  for (const [username,user] of users) {
    if (user.role != 'AUDIENCE') {
      user.round_score = 0;
    }
  }

  // Reset round member variables
  //local_Prompts = [];
  API_Prompts = [];
  round_Prompts = [];
  previousRoundPromptToAnswers = promptToAnswers;
  promptToAnswers = new Map();
  promptToAnswersIt = null;
  currentPromptToAnswer = null;

  startRound();
}


// Display client joined
function handleInitDisplay(socket) {
  console.log('[DISPLAY]: added main screen display client.');
  display_client_socket = socket;
}


// Display client leaves
function handleRemoveDisplay() {
  console.log('[DISPLAY]: removed main screen display client.');
  display_client_socket = null;
}


// Handle client communication
io.on('connection', socket => { 
  console.log('New connection');

  // Handle on chat message received, chat event is triggered
  socket.on('chat', message => {
    handleChat(message); // method to handle message
  });

  // Handle disconnection, when client closes tab
  socket.on('disconnect', () => {
    console.log('Dropped connection');
    handleQuit(socket);
    updateAll();
  });

  // Handle register
  socket.on('register', async (username, password) => {
    // Send API request for /player/register
    handleRegister(socket, username, password)
  });

  // Handle login
  socket.on('login', async (username, password) => {

    // Check if user has logged in already.
    if (Array.from(users.keys()).includes(username)) {
      // Tell client this account is already logegd in.
      console.log(username + ' has already logged in!')
      socket.emit('login-response', 'User has already logged in.')
      return;
    }
    handleLogin(socket, username, password)
  });

  // Handle successfully login
  socket.on('join', username => {
    if(socketsToUsers.has(socket)) return; // Don't update state of connected clients that haven't joined yet.
    handleJoin(socket, username);
    updateAll();
  });

  // Handle successfully login
  socket.on('logout', () => {
    if(!socketsToUsers.has(socket)) return; // Don't update state of connected clients that haven't joined yet.
    handleQuit(socket);
    updateAll();
  });

  // Handle admin actions
  socket.on('admin', action => {
    if(!socketsToUsers.has(socket)) return; // Don't update state of connected clients that haven't joined yet.
    handleAdmin(socket, action);
    updateAll();
  });

  // Handle sent prompts
  socket.on('submit-prompt', async prompt => {
    if(!socketsToUsers.has(socket)) return; // Don't update state of connected clients that haven't joined yet.
    handleSubmitPrompt(socket, prompt);
    updateAll();
  });

  // Handle sent answers
  socket.on('submit-answer', (prompt, answer) => {
    if(!socketsToUsers.has(socket)) return; // Don't update state of connected clients that haven't joined yet.

    const username = socketsToUsers.get(socket)
    console.log('Submitted answer by ' + username + ": " + answer);
    handleSubmitAnswer(socket, prompt, answer);
    updateAll();
  });

  // Handle sent votes
  socket.on('submit-vote', (prompt, username) => {
    if(!socketsToUsers.has(socket)) return; // Don't update state of connected clients that haven't joined yet.
    handleSubmitVote(socket, prompt, username);
    updateAll();
  });

  // Handle display client joining
  socket.on('init-display', () => {
    if(display_client_socket != null) return; // Only allow one display client
    handleInitDisplay(socket);
    updateAll();
  });

  // Handle display client joining
  socket.on('remove-display', () => {
    if(display_client_socket == null) return; // You can't delete a null disaply client
    handleRemoveDisplay(socket);
    updateAll();
  });


});


// API Requests are handled here
async function requestBackend(route, method_type, json_body) {
  console.log(method_type + ' method ' +  route + ' requested with body: ' + JSON.stringify(json_body));

  // Send response
  let url = BACKEND_ENDPOINT + route;
  try {
    const response = await fetch(url, {
      method: method_type,
      headers: {
        'Content-Type': 'application/json', // Ensures the server understands JSON format
      },
      body: JSON.stringify(json_body) // Add body only for POST
    });
    // Wait until the server gets the responses
    const data = await response.json()
    if (route != '/utils/get') {
      console.log('Success:', data);
    } else {
      console.log('Success: retrieved API prompts');
    }
    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}


// Start server if the script is run directly.
if (module === require.main) {
  startServer();
}

module.exports = server;
