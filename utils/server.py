from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import mimetypes
import logging
import cgi
import io

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/downloads/'):
            filename = self.path[11:]
            file_path = os.path.join('downloads', filename)
            if os.path.exists(file_path):
                self.send_response(200)
                content_type, _ = mimetypes.guess_type(file_path)
                self.send_header('Content-type', content_type or 'application/octet-stream')
                self.end_headers()
                with open(file_path, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_error(404, 'File not found')
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Hello, this is a GET request!')

    def do_POST(self):
        logging.info("Received POST request")
        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Handle JSON data
            if content_type == 'application/json':
                logging.info("Processing JSON data")
                json_data = self.rfile.read(content_length)
                
                try:
                    # Parse JSON to validate it
                    parsed_json = json.loads(json_data)
                    
                    # Generate a filename or use one from the URL if available
                    if '?' in self.path:
                        from urllib.parse import parse_qs
                        params = parse_qs(self.path.split('?')[1])
                        filename = params.get('filename', ['data.json'])[0]
                    else:
                        filename = f"data_{self.client_address[0]}_{int(time.time())}.json"
                    
                    # Ensure filename has .json extension
                    if not filename.endswith('.json'):
                        filename += '.json'
                    
                    # Ensure the filename is safe
                    filename = os.path.basename(filename)
                    file_path = os.path.join('uploads', filename)
                    
                    # Save JSON file
                    with open(file_path, 'w', encoding='utf-8') as file:
                        json.dump(parsed_json, file, indent=2)
                    
                    logging.info(f"JSON saved successfully: {file_path}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {'message': 'JSON received and saved', 'filename': filename}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON data: {str(e)}")
                    self.send_error(400, f"Invalid JSON: {str(e)}")
                
            elif content_type.startswith('multipart/form-data'):
                # Existing multipart/form-data handling
                pdict = dict(part.strip().split('=') for part in content_type.split(';')[1:])
                boundary = pdict.get('boundary', '').strip('"')
                pdict['boundary'] = boundary.encode('ascii')
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST',
                             'CONTENT_TYPE': self.headers['Content-Type']}
                )
                
                if 'file' in form:
                    fileitem = form['file']
                    filename = fileitem.filename if fileitem.filename else 'uploaded_file'
                    file_data = fileitem.file.read()
                else:
                    raise ValueError("No file found in the request")
                
                # Ensure the filename is safe
                filename = os.path.basename(filename)
                file_path = os.path.join('uploads', filename)
                
                with open(file_path, 'wb') as file:
                    file.write(file_data)
                
                logging.info(f"File saved successfully: {file_path}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'message': 'File received and saved', 'filename': filename}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            else:
                # Existing raw data handling
                content_length = int(self.headers['Content-Length'])
                file_data = self.rfile.read(content_length)
                filename = self.get_filename_from_header() or 'uploaded_file'

                # Ensure the filename is safe
                filename = os.path.basename(filename)
                file_path = os.path.join('uploads', filename)
                
                with open(file_path, 'wb') as file:
                    file.write(file_data)
                
                logging.info(f"File saved successfully: {file_path}")

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'message': 'File received and saved', 'filename': filename}
                self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            logging.error(f"Error processing POST request: {str(e)}")
            self.send_error(500, f"Internal server error: {str(e)}")

    def get_filename_from_header(self):
        if 'Content-Disposition' in self.headers:
            import re
            cd = self.headers['Content-Disposition']
            filename = re.findall('filename="?(.+)"?', cd)
            if filename:
                return filename[0]
        return None

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    logging.info(f'Server running on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    import time  # Added for timestamp in filenames
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('downloads', exist_ok=True)
    run_server()
