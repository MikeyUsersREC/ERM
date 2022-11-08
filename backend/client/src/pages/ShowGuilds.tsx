import axios from "axios";
import React, { useEffect, useState } from "react";
import { Guild, User } from "../types";
import config from "../config.json";
import { Loading } from "../components/Loading";
import Particle from "./Particles";

export const ShowGuilds: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [guilds, setGuilds] = useState<Array<Guild> | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const accessToken = localStorage.getItem("access_token");

    const makeRequests = async () => {
      if (accessToken) {
        const userRes = await axios.get(`${config.API_URL}/users/me`, {
          headers: {
            access_token: accessToken,
          },
        });
        setUser(userRes.data);
        await new Promise((r) => setTimeout(r, 250));
        const guildsRes = await axios.get(`${config.API_URL}/guilds`, {
          headers: {
            access_token: accessToken,
          },
        });
        setGuilds(guildsRes.data.guilds);
        setLoading(false);
      } else {
        window.location.href = "/login";
      }
    };

    makeRequests();
  }, []);

  console.log(guilds);
  if (loading) {
    return <Loading />;
  }


  return (
    <>
      <Particle />
      <div className="container mx-auto">
        <div className="flex items-center h-screen justify-center">
          <div className="h-3/4">
            <h1 className="text-white text-4xl mb-16 text-center">Mutual Servers</h1>
            <div className="pt-10 pb-14 h-64 grid grid-cols-3 gap-8">
              {guilds?.map((guild: Guild) => {
                return (
                  <div
                    onClick={() =>
                      (window.location.href = `/guilds/${guild.id}`)
                    }
                    className="transition duration-500 transform hover:scale-110 rounded text-white mb-12 cursor-pointer"
                    style={{background: "#1D1D1D"}}
                  >
                    <div className="flex justify-center -mt-16">
                      <img
                        className="rounded-full"
                        width="150"
                        src={guild.icon_url}
                      />
                    </div>
                    <div className="px-6 py-4">
                      <h1 className="text-xl font-semibold break-words text-center">
                        {guild.name}
                      </h1>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
