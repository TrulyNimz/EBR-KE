import { DefaultSession, DefaultUser } from 'next-auth';
import { DefaultJWT } from 'next-auth/jwt';

declare module 'next-auth' {
  interface Session extends DefaultSession {
    user: {
      id: string;
      role: string;
      tenants: string[];
      permissions: string[];
    } & DefaultSession['user'];
    accessToken: string;
  }

  interface User extends DefaultUser {
    role: string;
    tenants: string[];
    permissions: string[];
    accessToken: string;
    refreshToken: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    id: string;
    role: string;
    tenants: string[];
    permissions: string[];
    accessToken: string;
    refreshToken: string;
    accessTokenExpires: number;
  }
}
