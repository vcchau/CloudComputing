import ast
import boto3
import logging
import os
import sys
import traceback

LOG_FILE_NAME = 'output.log'

REGION = 'us-west-2'

class S3Handler:
    """S3 handler."""

    def __init__(self):
        self.client = boto3.client('s3')

        logging.basicConfig(filename=LOG_FILE_NAME,
                            level=logging.DEBUG, filemode='w',
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        self.logger = logging.getLogger("S3Handler")

    def help(self):
        print("Supported Commands:")
        print("1. createdir <bucket_name>")
        print("2. upload <source_file_name> <bucket_name> [<dest_object_name>]")
        print("3. download <dest_object_name> <bucket_name> [<source_file_name>]")
        print("4. delete <dest_object_name> <bucket_name>")
        print("5. deletedir <bucket_name>")
        print("6. find <file_extension> [<bucket_name>] -- e.g.: 1. find txt  2. find txt bucket1 --")
        print("7. listdir [<bucket_name>]")

    def _error_messages(self, issue):
        error_message_dict = {}
        error_message_dict['incorrect_parameter_number'] = 'Incorrect number of parameters provided'
        error_message_dict['not_implemented'] = 'Functionality not implemented yet!'
        error_message_dict['bucket_name_exists'] = 'Directory already exists.'
        error_message_dict['bucket_name_empty'] = 'Directory name cannot be empty.'
        error_message_dict['missing_source_file'] = 'Source file cannot be found.'
        error_message_dict['non_existent_bucket'] = 'Directory does not exist.'
        error_message_dict['non_existent_object'] = 'Destination Object does not exist.'
        error_message_dict['unknown_error'] = 'Something was not correct with the request. Try again.'

        if issue:
            return error_message_dict[issue]
        else:
            return error_message['unknown_error']

    def _get_file_extension(self, file_name):
        if os.path.exists(file_name):
            return os.path.splitext(file_name)

    def _get(self, bucket_name):
        response = ''
        try:
            response = self.client.head_bucket(Bucket=bucket_name)
        except Exception as e:
            # print(e)
            # traceback.print_exc(file=sys.stdout)

            response_code = e.response['Error']['Code']
            if response_code == '404':
                return False
            elif response_code == '200':
                return True
            else:
                raise e
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            return False

    def createdir(self, bucket_name):
        if not bucket_name:
            return self._error_messages('bucket_name_empty')

        try:
            if self._get(bucket_name):
                return self._error_messages('bucket_name_exists')
            self.client.create_bucket(Bucket=bucket_name,
                                      CreateBucketConfiguration={'LocationConstraint': REGION})
        except Exception as e:
            print(e)
            raise e

        # Success response
        operation_successful = ('Directory %s created.' % bucket_name)
        return operation_successful

    def listdir(self, bucket_name):
        s3 = boto3.resource('s3')
        resource_list = ''
        # If bucket_name is empty then display the names of all the buckets
        if not bucket_name:
            for bucket in s3.buckets.all():
                resource_list += bucket.name
                resource_list += ', '

        # Bucket_name is not empty; list contents of the bucket
        else:
            try:
                # If bucket_name is provided, check that bucket exits.
                bucket = s3.Bucket(bucket_name)

                # If bucket_name is provided then display the names of all objects in the bucket
                for obj in bucket.objects.all():
                    resource_list += obj.key
                    resource_list += ', '

                # Cut out extra comma
                if resource_list:
                    resource_list = resource_list[:-2]

            except:
                return self._error_messages('non_existent_bucket')

        return resource_list

    def upload(self, source_file_name, bucket_name, dest_object_name):
        # 1. Parameter Validation
        #    - source_file_name exits in current directory
        #    - bucket_name exists
        try:
            response = self.client.head_bucket(Bucket = bucket_name)

            # Verify the source file exists
            try:
                s3 = boto3.resource('s3')
                # 2. If dest_object_name is not specified then use the source_file_name as dest_object_name
                if not dest_object_name:
                    dest_object_name = source_file_name

                extension = self._get_file_extension(source_file_name)
                metadata = {'metadata' : extension[1]}

                # Attempt to upload the file to the bucket
                try:
                    # 3. SDK call
                    #    - When uploading the source_file_name and add it to object's meta-data
                    #    - Use self._get_file_extension() method to get the extension of the file.
                    s3.meta.client.upload_file(source_file_name, bucket_name, dest_object_name,
                        ExtraArgs = {'Metadata':
                                        {'Metadata' : metadata['metadata']},
                                    })

                except:
                    return self._error_messages('unknown_error')

            except:
                return self._error_messages('missing_source_file')

        except:
            return self._error_messages('non_existent_bucket')

        # Success response
        operation_successful = ('File %s uploaded to bucket %s.' % (source_file_name, bucket_name))

        return operation_successful


    def download(self, dest_object_name, bucket_name, source_file_name=''):
        # if source_file_name is not specified then use the dest_object_name as the source_file_name
        # If the current directory already contains a file with source_file_name then move it as a backup
        # with following format: <source_file_name.bak.current_time_stamp_in_millis>

        # Parameter Validation

        # SDK Call

        # Success response
        operation_successful = ('Object %s downloaded from bucket %s.' % (dest_object_name, bucket_name))

        return operation_successful

    def delete(self, dest_object_name, bucket_name):
        # Verify if the bucket exists
        try:
            response = self.client.head_bucket(Bucket = bucket_name)

            # Verify the object exists
            try:
                response = self.client.head_object(Bucket = bucket_name, Key = dest_object_name)

                # Attempt to delete the object
                try:
                    response = self.client.delete_object(Bucket = bucket_name, Key = dest_object_name)

                except:
                    return self._error_messages('unknown_error')

            except:
                return self._error_messages('non_existent_object')

        except:
            return self._error_messages('non_existent_bucket')

        # Success response
        operation_successful = ('Object %s deleted from bucket %s.' % (dest_object_name, bucket_name))

        return operation_successful


    def deletedir(self, bucket_name):
        # Delete the bucket only if it is empty
        try:
            response = self.client.head_bucket(Bucket = bucket_name)

            # Grab the bucket
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(bucket_name)

            empty = True
            for obj in bucket.objects.all():
                empty = False
                break

            # Verify whether bucket isd empty
            if empty:
                # Attempt to delete the empty bucket
                try:
                    response = self.client.delete_bucket(Bucket = bucket_name)

                except Exception as e:
                    return self._error_messages('unknown_error')
            else:
                print('The directory is not empty')
                return self._error_messages('unknown_error')

        except Exception as e:
            return self._error_messages('non_existent_bucket')

        # Success response
        operation_successful = ("Deleted bucket %s." % bucket_name)

        return operation_successful


    def find(self, file_extension, bucket_name=''):
        # Return object names that match the given file extension

        # If bucket_name is specified then search for objects in that bucket.
        # If bucket_name is empty then search all buckets



        return self._error_messages('not_implemented')


    def dispatch(self, command_string):
        parts = command_string.split(" ")
        response = ''

        if parts[0] == 'createdir':
            # Figure out bucket_name from command_string
            if len(parts) > 1:
                bucket_name = parts[1]
                response = self.createdir(bucket_name)
            else:
                # Parameter Validation
                # - Bucket name is not empty
                response = self._error_messages('bucket_name_empty')
        elif parts[0] == 'upload':
            # Figure out parameters from command_string
            # source_file_name and bucket_name are compulsory; dest_object_name is optional
            # Use self._error_messages['incorrect_parameter_number'] if number of parameters is less
            # than number of compulsory parameters
            if len(parts) > 2:
                source_file_name = parts[1]
                bucket_name = parts[2]
                dest_object_name = ''

                if len(parts) > 3:
                    dest_object_name = parts[3]

                response = self.upload(source_file_name, bucket_name, dest_object_name)

            else:
                response = self._error_messages('incorrect_parameter_number')

        elif parts[0] == 'download':
            # Figure out parameters from command_string
            # dest_object_name and bucket_name are compulsory; source_file_name is optional
            # Use self._error_messages['incorrect_parameter_number'] if number of parameters is less
            # than number of compulsory parameters
            if len(parts) > 2:
                dest_object_name = parts[1]
                bucket_name = parts[2]
                source_file_name = ''

                if len(parts) > 3:
                    source_file_name = parts[3]

                response = self.download(dest_object_name, bucket_name, source_file_name)

            else:
                response = self._error_messages('incorrect_parameter_number')

        elif parts[0] == 'delete':
            if len(parts) > 2:
                dest_object_name = parts[1]
                bucket_name = parts[2]
                response = self.delete(dest_object_name, bucket_name)

            else:
                response = self._error_messages('incorrect_parameter_number')

        elif parts[0] == 'deletedir':
            if len(parts) > 1:
                bucket_name = parts[1]
                response = self.deletedir(bucket_name)

            else:
                response = self._error_messages('incorrect_parameter_number')

        elif parts[0] == 'find':
            if len(parts) > 2:
                file_extension = parts[1]
                bucket_name = parts[2]
                response = self.find(file_extension, bucket_name)

            else:
                response = self._error_messages('incorrect_parameter_number')

        elif parts[0] == 'listdir':
            bucket_name = ''
            if len(parts) > 1:
                bucket_name = parts[1]

            response = self.listdir(bucket_name)

        else:
            response = "Command not recognized."
        return response


def main():

    s3_handler = S3Handler()

    while True:
        try:
            command_string = ''
            if sys.version_info[0] < 3:
                command_string = raw_input("Enter command ('help' to see all commands, 'exit' to quit)>")
            else:
                command_string = input("Enter command ('help' to see all commands, 'exit' to quit)>")

            # Remove multiple whitespaces, if they exist
            command_string = " ".join(command_string.split())

            if command_string == 'exit':
                print("Good bye!")
                exit()
            elif command_string == 'help':
                s3_handler.help()
            else:
                response = s3_handler.dispatch(command_string)
                print(response)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    main()
