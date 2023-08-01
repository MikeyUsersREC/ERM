import React, { useEffect, useState } from "react";
import Particle from "./Particles";
import axios from "axios";
import { User } from "../types";
import config from "../config.json";
import { Loading } from "../components/Loading";

function Homepage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const accessToken = localStorage.getItem("access_token");

    if (accessToken) {
      axios
        .get(`${config.API_URL}/users/me`, {
          headers: {
            access_token: accessToken,
          },
        })
        .then((resp) => {
          const user: User = resp.data;
          setUser(user);
          setLoading(false);
        })
        .catch(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) {
    return <Loading />;
  }

  return (
    <>
      <Particle />
      <div className="container mx-auto md:container md:mx-auto text-center h-screen">
        <div className="flex h-full justify-center items-center">
          <div className="container mx-auto">
            <img
              src="https://cdn.discordapp.com/avatars/978662093408591912/ef1f8ed7c6eec92e125e9c2bbc6fa9ae.png"
              className="inline mb-5 rounded-full"
              alt=""
            />
            <h1
              className="text-white text-6xl mb-5"
              style={{ fontFamily: "'Ubuntu', sans-serif" }}
            >
              ERM
            </h1>
            {!user ? (
              <button
                className="bg-red-900 hover:bg-red-800 text-white font-semibold py-2 px-4 rounded"
                onClick={() => {
                  window.location.href = "/login";
                }}
              >
                Log In with Discord
              </button>
            ) : (
              <div>
                <h1 className="text-white text-xl mb-4">
                  Logged in as{" "}
                  <span className="font-semibold">
                    {user.username}#{user.discriminator}
                  </span>
                </h1>
                <button
                  className="bg-red-900 hover:bg-red-800 text-white font-semibold py-2 px-4 rounded mb-2"
                  onClick={() => {
                    window.location.href = "/guilds";
                  }}
                >
                  Go to Dashboard
                </button><br/>
                <button
                  className="bg-red-900 hover:bg-red-800 text-white font-semibold py-2 px-4 rounded"
                  onClick={() => {
                    window.location.href = "/logout";
                  }}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default Homepage;
