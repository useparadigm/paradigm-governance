import { saveUser } from '../db/repository';
import { User } from './models';

export function createDefaultUser(): User {
    const user = new User('default', 'default@example.com');
    saveUser(user);
    return user;
}
