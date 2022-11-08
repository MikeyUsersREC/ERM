import React, { useEffect } from "react";
import queryString from "query-string";
import axios from "axios";

import config from "../config.json";

interface TokenResponse {
  access_token: string | null;
}

export const CallbackHandler: React.FC = (props: any) => {
  const interpreted = queryString.parse(props.location.search);
  console.log(interpreted);
  console.log(props.location);

  useEffect(() => {
    axios
      .post(`${config.API_URL}/oauth2/callback`, {
        code: code,
      })
      .then((res) => {
        const data: TokenResponse = res.data;
        console.log(res.data);
        console.log(data);
        if (data.access_token === null) {
          window.location.href = "/login";
        } else {
          localStorage.setItem("access_token", data.access_token);
          window.location.href = "/";
        }
      });
  }, []);

  const code = interpreted.code;

  return (
    <div className="h-screen flex items-center justify-center">
      <h1 className="text-white text-5xl text-center">Redirecting...</h1>
    </div>
  );
};
