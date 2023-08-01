import React from "react";
import { BrowserRouter, Switch, Route } from "react-router-dom";
import { CallbackHandler } from "./pages/CallbackHandler";
import Homepage from "./pages/Homepage";
import { Login } from "./pages/Login";
import { Logout } from "./pages/Logout";
import { ShowGuilds } from "./pages/ShowGuilds";

export const Router: React.FC = () => {
  return (
    <BrowserRouter>
      <Switch>
        <Route exact path="/" component={Homepage} />
        <Route exact path="/login" component={Login} />
        <Route exact path="/logout" component={Logout} />
        <Route exact path="/callback" component={CallbackHandler} />
        <Route exact path="/guilds" component={ShowGuilds} />
      </Switch>
    </BrowserRouter>
  );
};
