import { User } from '@/core/models';
import { saveUser, getUser } from '../db/repository';
import { formatResponse } from '@/utils/helpers';

export function createUser(name: string, email: string) {
    const user = new User(name, email);
    saveUser(user);
    return formatResponse({ id: 1, name });
}

export function getUserRoute(userId: number) {
    const user = getUser(userId);
    return formatResponse({ name: user.name });
}
