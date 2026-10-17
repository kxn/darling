# Download/resolve gems with the host's TLS client for Darling's older Ruby.
# Installation and execution of CocoaPods itself happen under Darling.
require 'rubygems'
require 'rubygems/request_set'
require 'rubygems/remote_fetcher'
require 'rubygems/spec_fetcher'
require 'rubygems/package'
require 'json'

def Gem.ruby_version
  Gem::Version.new('2.6.3')
end
def Gem.rubygems_version
  Gem::Version.new('3.4.22')
end
Gem.platforms = [Gem::Platform::RUBY, Gem::Platform.new('x86_64-darwin')]
class << Gem::Platform
  def local(*args)
    Gem::Platform.new('x86_64-darwin')
  end
end
destination = File.expand_path('../runtime/gem-prefetch', __dir__)
requests = Gem::RequestSet.new
requests.gem('cocoapods', '= 1.16.2')
requests.gem('xcodeproj', '= 1.27.0')
requests.gem('rexml', '= 3.3.9')
requests.gem('ffi', '= 1.17.2')
requests.gem('CFPropertyList', '= 3.0.6')
requests.gem('json', '= 2.1.0')
requests.gem('concurrent-ruby', '= 1.3.4')
requests.resolve
manifest = requests.sorted_requests.map do |request|
  path = request.download(destination)
  puts "Downloaded #{request.full_name}"
  {name: request.name, version: request.version.to_s, platform: request.platform.to_s, path: path}
end
File.write(File.join(destination, 'manifest.json'), JSON.pretty_generate(manifest)+"\n")
