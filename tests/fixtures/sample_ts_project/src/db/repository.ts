import { User, Project } from '@/core/models';

export function saveUser(user: User): void {}

export function getUser(userId: number): User {
    return new User('test', 'test@example.com');
}

export function saveProject(project: Project): void {}
