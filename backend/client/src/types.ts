export interface User {
    id: string;
    username: string;
    discriminator: number;
    avatar_url: string;
}

export interface Guild {
    id: string;
    name: string;
    icon_url: string;
}