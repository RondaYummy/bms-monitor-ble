import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModuleAsyncOptions } from '@nestjs/typeorm';
import { join } from 'path';

export const typeormConfig: TypeOrmModuleAsyncOptions = {
  imports: [ConfigModule],
  inject: [ConfigService],
  useFactory: (configService: ConfigService) => ({
    type: configService.get<any>('DATABASE_TYPE'),
    host: configService.get<string>('DATABASE_HOST'),
    username: configService.get<string>('DATABASE_USER'),
    password: configService.get<string>('DATABASE_PASSWORD'),
    database: configService.get<string>('DATABASE_NAME'),
    port: configService.get<number>('DATABASE_PORT'),
    entities: [join(__dirname, '**', '*.entity.{ts,js}')],
    migrations: ['dist/migrations/*{.ts,.js}'],
    migrationsRun: true,
    synchronize: true,
    uuidExtension: 'uuid-ossp',
    autoLoadEntities: true,
    logger: 'advanced-console',
    useUTC: true,
    logging: 'all',
  }),
};
