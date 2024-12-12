var socket = null;

// Prepare game
var app = new Vue({
    el: '#game',
    data: {
        error: null, // To catch errors

        // Server's state
        server_state: { state: 0, round: 0, prompt_vote: null, leaderboard: {}},
        // server_state.state -> 0: Lobby, 1: Prompt, 2: Answers, 3: Voting, 4: Vote results, 5: Round Scores, 6: Game Over
        // { prompt: "prompt", player_1: {username: "username", answer: "answer", votes: }, player_2: {username: "username", answer: "answer"} ]} }
        users: {},
        user_count: 0,

        // Client's state with the server
        user_state: { username: null, state: 0, games_played: 0, round_score: 0, total_score: 0, role: '', promptQ1: null, promptQ2: null, current_prompt: null },
        // state -> 0: Waiting in lobby, 1: Writing 1st prompt, 2: Sent a prompt 3: Answering prompts, 4: Waiting answers
        // 5: Voting, 6: Waiting Votes, 7: Viewing Votes, 8: Showing round scores, 9: Game Over

        prompt_state: { state: 0, everyone_answered: false, all_players_answered_prompts: false },
        // 0: Currently writing, 1: Non-existent player, 2: Invalid prompt, 3: Unsupported langauge, 4: Sent a prompt
        promptSuggestion: '', // User's suggested prompt
        promptAnswer: '', // User's prompt answer

        display: { promptsSent: [], prompt_num: 0, whosAnswering: [], whosAnswered: [] },

        // Client's login state
        client_state: { state: false, login: null },
        // state -> false: not connected, 0: connected, 1: logged in, -1: Display client
        // login -> 0: registered, 1: user already exists, 2: inavlid username, 
        //3: invalid password, 4: failed to login 5: A user has already logged in
        username: '', // Clients inputted username
        password: '', // Clients inputted password
        playername: '', // Clients username when successfully logged in

        leaderboard: [], 
        podium: {},
        url: '',
    },
    mounted: function() {
        connect(); 
    },
    methods: {
        handleRegister(message) {
            switch (message){
                case 'OK': 
                    this.client_state.login = 0;
                    break;
                case 'Username already exists': 
                    this.client_state.login = 1; 
                    break;
                case 'Username less than 4 characters or more that 14 characters':
                    this.client_state.login = 2; 
                    break;
                case 'Password less than 10 characters or more than 20 characters':
                    this.client_state.login = 3; 
                    break;
            }
        },
        handleLogin(message) {
            switch (message){
                case 'OK':
                    this.client_state.state = 1;
                    socket.emit('join',this.playername) // Send username to server when successfully logged in
                    break;
                case 'Username or password incorrect':
                    this.client_state.login = 4; 
                    this.playername = ''; // Remove if failed to log in
                    break;
                case 'User has already logged in.':
                    this.client_state.login = 5;
                    this.playername = '';
                    break;
            }
        },
        handlePrompt(message) {
            switch (message){
                case 'Player does not exist': 
                    this.prompt_state.state = 1; 
                    break;
                case 'Prompt less than 20 characters or more than 100 characters':
                    this.prompt_state.state = 2; 
                    break;
                case 'Unsupported language':
                    this.prompt_state.state = 3; 
                    break;
                case 'OK':
                    this.prompt_state.state = 4;
                    break;
                case 'OK, all players answered':
                    this.prompt_state.state = 4;
                    this.prompt_state.everyone_answered = true;
                    break;
                case 'OK, all players answered the prompts':
                    this.prompt_state.all_players_answered_prompts = true;
            }
        },
        register() {
            if(this.username != '' && this.password != '') {
                // Only send API request if the fields are filled in
                socket.emit('register',this.username,this.password);
                this.username = '';
                this.password = '';
            }
        },
        login() {
            if(this.username != '' && this.password != '') {
                // Only send to server if the fields are filled
                socket.emit('login', this.username, this.password); 
                this.playername = this.username; // Store in case it logs in
                this.username = '';
                this.password = '';
            }
        },
        update(data) {
            this.server_state = data.server_state;
            this.user_state = data.user_state;
            this.users = data.users;
            this.user_count = data.user_count;
            this.podium = data.podium;
        },
        updateDisplay(data) {
            this.client_state.state = -1;
            this.server_state = data.server_state;
            this.users = data.users;
            this.user_count = data.user_count;
            this.podium = data.podium;
            this.url = data.url;
        },
        updatePromptCount(username) {
            this.display.promptsSent.push(username);
            this.display.prompt_num = this.display.promptsSent.length;
        },
        logout() {
            // Reset states
            socket.emit('logout');
            this.server_state = { state: 0, round: 0, prompt_vote: null, leaderboard: {}};
            this.user_state = { username: null, state: 0, games_played: 0, round_score: 0, total_score: 0, role: '', promptQ1: null, promptQ2: null, current_prompt: null };
            this.client_state = { state: 0, login: null };
        },
        admin(action) {
            socket.emit('admin',action);
        },
        sendPrompt() {
            if (this.prompt != '') {
                // Only send to server if the fields are filled
                socket.emit('submit-prompt', this.promptSuggestion);
                this.promptSuggestion = '';
            } 
        },
        sendAnswer() {
            if (this.promptAnswer != '') {
                // Only send to server if the fields are filled
                socket.emit('submit-answer', this.user_state.current_prompt, this.promptAnswer);
                this.promptAnswer = '';
            } 
        },
        sendVote(username) {
            socket.emit('submit-vote', this.server_state.prompt_vote.prompt, username);
        },
        leaveGameOver() {
            // Safely leave lobby, reset all states
            server_state = { state: 0, round: 0, prompt_vote: null }
            users = {}
            user_count = 0,
            user_state = { username: null, state: 0, games_played: 0, round_score: 0, total_score: 0, role: '', 
                promptQ1: null, promptQ2: null, current_prompt: null }
        },
        initDisplay() {
            // Add main display
            socket.emit('init-display');

        },
        removeDisplay() {
            // Reset states
            socket.emit('remove-display');
            this.server_state = { state: 0, round: 0, prompt_vote: null, leaderboard: {}};
            this.user_state = { username: null, state: 0, games_played: 0, round_score: 0, total_score: 0, role: '', promptQ1: null, promptQ2: null, current_prompt: null };
            this.client_state = { state: 0, login: null };
        }
    }
});

// Handle server communication
function connect() {
    // Prepare web socket
    socket = io();

    // Connect
    socket.on('connect', function() {
        app.client_state.state = 0;
    });

    // Handle connection error
    socket.on('connect_error', function(message) {
        alert('Unable to connect: ' + message);
    });

    // Handle disconnection
    socket.on('disconnect', function() {
        alert('Disconnected');
        app.client_state.state = false;
    });

    // Handle incoming chat message
    socket.on('chat', function(message) {
        app.handleChat(message);
    });

    // Handle register, update client
    socket.on('register-response', function(message) {
        app.handleRegister(message);
    });

    // Handle login, update client
    socket.on('login-response', function(message) {
        app.handleLogin(message);
    });

    // Update list of users and their details
    socket.on('update-user', function(message) {
        app.update(message);
    });

    // Send user the prompt response.
    socket.on('prompt-response', function(message) {
        app.handlePrompt(message);
    });

    // Send user to reset prompt states.
    socket.on('reset-prompt-state', function() {
        app.prompt_state.state = 0;
        app.prompt_state.everyone_answered = false;
        app.prompt_state.all_players_answered_prompts = false;
    });

    // Update display client.
    socket.on('update-display', function(message) {
        app.updateDisplay(message);
    });

    // Update prompt count.
    socket.on('increment-prompt-count', function(message) {
        app.updatePromptCount(message);
    });

    // Reset prompt count.
    socket.on('reset-prompt-display', function() {
        app.display.promptsSent = [];
        app.display.prompt_num = 0;
        app.display.whosAnswered = [];
        app.display.whosAnswering = [];
    });

    // Initalise answer display.
    socket.on('add-player-whos-answering', function(username) {
        app.display.whosAnswering.push(username);
    });

    // Update answer display.
    socket.on('add-player-whos-answered', function(username) {
        app.display.whosAnswering = app.display.whosAnswering.filter(item => item != username);
        app.display.whosAnswered.push(username);
    });

}
