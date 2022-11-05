import React from 'react';

function App() {
  return (
    <div>
      <a href="https://discord.com/api/oauth2/authorize?client_id=1001927179917066240&redirect_uri=http%3A%2F%2F127.0.0.1%3A5000%2Foauth2%2Fcallback&response_type=code&scope=identify%20guilds"><button>Login with Discord</button></a>
    </div>
  );
}

export default App;
