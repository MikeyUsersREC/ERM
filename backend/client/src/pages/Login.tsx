import React from "react";
import config from "../config.json";

export const Login: React.FC = () => {
  window.location.href = config.OAUTH_URL;
  return <div></div>;
};
