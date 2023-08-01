import React from "react";

export const Loading: React.FC = () => {
  return (
    <div>
      <div className="container mx-auto md:container md:mx-auto text-center h-screen">
        <div className="flex h-full justify-center items-center">
          <img
            className="animate-spin h-50 w-50 mr-3"
            src="https://cdn.discordapp.com/avatars/978662093408591912/ef1f8ed7c6eec92e125e9c2bbc6fa9ae.png"
            alt=""
          />
        </div>
      </div>
    </div>
  );
};
