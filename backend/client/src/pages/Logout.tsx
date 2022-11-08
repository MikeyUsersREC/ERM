import React from "react";

export const Logout: React.FC = () => {
  localStorage.removeItem("access_token");
  window.location.href = "/";
  return <div></div>;
};
