import { plainToClass } from 'class-transformer';
import { IsNotEmpty, IsString, validateSync } from 'class-validator';

class EnvironmentVariables {
  @IsString()
  @IsNotEmpty()
  TELEGRAM_BOT_TOKEN: string;
  @IsString()
  @IsNotEmpty()
  DATABASE_NAME: string;
  @IsString()
  @IsNotEmpty()
  DATABASE_USER: string;
  @IsString()
  @IsNotEmpty()
  DATABASE_TYPE: string;
  @IsString()
  @IsNotEmpty()
  DATABASE_PASSWORD: string;
  @IsNotEmpty()
  DATABASE_PORT: string;
}

export function validate(config: Record<string, unknown>) {
  const validatedConfig = plainToClass(EnvironmentVariables, config, {
    enableImplicitConversion: true,
  });
  const errors = validateSync(validatedConfig, {
    skipMissingProperties: false,
  });

  if (errors.length > 0) {
    throw new Error(errors.toString());
  }
  return validatedConfig;
}
